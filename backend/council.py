"""3-stage LLM Council orchestration."""

from typing import List, Dict, Any, Tuple, Optional
import asyncio
import uuid
from .openrouter import query_models_parallel, query_model, query_model_stream
from .config import get_council_models, get_chairman_model, AVAILABLE_MODELS, get_enhanced_features, get_model_persona
from .tools import web_search, execute_python, get_memory_context, remember_decision


async def stage1_collect_responses(user_query: str, context: Optional[str] = None, user_id: Optional[uuid.UUID] = None, db: Optional[Any] = None) -> List[Dict[str, Any]]:
    """
    Stage 1: Collect individual responses from all council models.

    Args:
        user_query: The user's question
        context: Optional conversation context from previous exchanges
        user_id: Optional user ID for user-specific API keys
        db: Optional database session for resolving API keys

    Returns:
        List of dicts with 'model' and 'response' keys
    """
    # Build the query with context if available
    if context:
        enhanced_query = f"{context}\n\n---\n\nCurrent Question: {user_query}"
    else:
        enhanced_query = user_query

    # Build messages with persona if assigned
    # Get user-specific council models if available
    if user_id and db:
        from .database import crud as db_crud
        settings = await db_crud.settings.get_by_user_id(db, user_id)
        if settings and settings.council_models:
            council_models = settings.council_models
        else:
            council_models = get_council_models()
    else:
        council_models = get_council_models()
    messages_by_model = {}

    for model in council_models:
        persona = get_model_persona(model)
        if persona:
            # Prepend system message with persona
            messages_by_model[model] = [
                {"role": "system", "content": persona},
                {"role": "user", "content": enhanced_query}
            ]
        else:
            # No persona, just user message
            messages_by_model[model] = [{"role": "user", "content": enhanced_query}]

    # Query all models in parallel (with user-specific API keys)
    responses = await query_models_parallel(council_models, messages_by_model, user_id=user_id, db=db)

    # #region agent log
    import os
    import json
    from datetime import datetime
    debug_log_path = os.getenv("DEBUG_LOG_PATH", "/Users/sezars/llm-council/.cursor/debug.log")
    if os.path.exists(os.path.dirname(debug_log_path)):
        try:
            successful = sum(1 for r in responses.values() if r is not None)
            failed = len(responses) - successful
            with open(debug_log_path, 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"stage1-collect","hypothesisId":"H2","location":"council.py:56","message":"stage1_responses_collected","data":{"total_models":len(council_models),"successful":successful,"failed":failed,"user_id":str(user_id) if user_id else None},"timestamp":int(datetime.now().timestamp()*1000)}) + '\n')
        except Exception:
            pass
    # #endregion

    # Format results
    stage1_results = []
    for model, response in responses.items():
        if response is not None:  # Only include successful responses
            result = {
                "model": model,
                "response": response.get('content', '')
            }
            # Include thinking tokens if available (for reasoning models)
            if 'thinking' in response:
                result['thinking'] = response.get('thinking')
            stage1_results.append(result)
        else:
            # #region agent log
            if os.path.exists(os.path.dirname(debug_log_path)):
                try:
                    with open(debug_log_path, 'a') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"stage1-collect","hypothesisId":"H3","location":"council.py:69","message":"stage1_model_failed","data":{"model":model,"user_id":str(user_id) if user_id else None},"timestamp":int(datetime.now().timestamp()*1000)}) + '\n')
                except Exception:
                    pass
            # #endregion

    return stage1_results


async def stage2_collect_rankings(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    user_id: Optional[uuid.UUID] = None,
    db: Optional[Any] = None
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Stage 2: Each model ranks the anonymized responses.

    Args:
        user_query: The original user query
        stage1_results: Results from Stage 1

    Returns:
        Tuple of (rankings list, label_to_model mapping)
    """
    # Create anonymized labels for responses (Response A, Response B, etc.)
    labels = [chr(65 + i) for i in range(len(stage1_results))]  # A, B, C, ...

    # Create mapping from label to model name
    label_to_model = {
        f"Response {label}": result['model']
        for label, result in zip(labels, stage1_results)
    }

    # Build the ranking prompt
    responses_text = "\n\n".join([
        f"Response {label}:\n{result['response']}"
        for label, result in zip(labels, stage1_results)
    ])

    ranking_prompt = f"""You are evaluating different responses to the following question:

Question: {user_query}

Here are the responses from different models (anonymized):

{responses_text}

Your task:
1. First, evaluate each response individually. For each response, explain what it does well and what it does poorly.
2. Then, at the very end of your response, provide a final ranking.

IMPORTANT: Your final ranking MUST be formatted EXACTLY as follows:
- Start with the line "FINAL RANKING:" (all caps, with colon)
- Then list the responses from best to worst as a numbered list
- Each line should be: number, period, space, then ONLY the response label (e.g., "1. Response A")
- Do not add any other text or explanations in the ranking section

Example of the correct format for your ENTIRE response:

Response A provides good detail on X but misses Y...
Response B is accurate but lacks depth on Z...
Response C offers the most comprehensive answer...

FINAL RANKING:
1. Response C
2. Response A
3. Response B

Now provide your evaluation and ranking:"""

    messages = [{"role": "user", "content": ranking_prompt}]

    # Get user-specific council models if available
    if user_id and db:
        from .database import crud as db_crud
        settings = await db_crud.settings.get_by_user_id(db, user_id)
        if settings and settings.council_models:
            council_models = settings.council_models
        else:
            council_models = get_council_models()
    else:
        council_models = get_council_models()

    # Get rankings from all council models in parallel (with user-specific API keys)
    responses = await query_models_parallel(council_models, messages, user_id=user_id, db=db)

    # Format results
    stage2_results = []
    for model, response in responses.items():
        if response is not None:
            full_text = response.get('content', '')
            parsed = parse_ranking_from_text(full_text)
            stage2_results.append({
                "model": model,
                "ranking": full_text,
                "parsed_ranking": parsed
            })

    return stage2_results, label_to_model


async def stage3_synthesize_final(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]],
    user_id: Optional[uuid.UUID] = None,
    db: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Stage 3: Chairman synthesizes final response.

    Args:
        user_query: The original user query
        stage1_results: Individual model responses from Stage 1
        stage2_results: Rankings from Stage 2

    Returns:
        Dict with 'model' and 'response' keys
    """
    # Build comprehensive context for chairman
    stage1_text = "\n\n".join([
        f"Model: {result['model']}\nResponse: {result['response']}"
        for result in stage1_results
    ])

    stage2_text = "\n\n".join([
        f"Model: {result['model']}\nRanking: {result['ranking']}"
        for result in stage2_results
    ])

    chairman_prompt = f"""You are the Chairman of an LLM Council. Multiple AI models have provided responses to a user's question, and then ranked each other's responses.

Original Question: {user_query}

STAGE 1 - Individual Responses:
{stage1_text}

STAGE 2 - Peer Rankings:
{stage2_text}

Your task as Chairman is to synthesize all of this information into a single, comprehensive, accurate answer to the user's original question. Consider:
- The individual responses and their insights
- The peer rankings and what they reveal about response quality
- Any patterns of agreement or disagreement

Provide a clear, well-reasoned final answer that represents the council's collective wisdom:"""

    messages = [{"role": "user", "content": chairman_prompt}]

    # Get user-specific chairman model if available
    if user_id and db:
        from .database import crud as db_crud
        settings = await db_crud.settings.get_by_user_id(db, user_id)
        if settings and settings.chairman_model:
            chairman = settings.chairman_model
        else:
            chairman = get_chairman_model()
    else:
        chairman = get_chairman_model()
    
    # Query the chairman model (with user-specific API keys)
    response = await query_model(chairman, messages, user_id=user_id, db=db)

    if response is None:
        # Fallback if chairman fails
        return {
            "model": chairman,
            "response": "Error: Unable to generate final synthesis."
        }

    return {
        "model": chairman,
        "response": response.get('content', '')
    }


def parse_ranking_from_text(ranking_text: str) -> List[str]:
    """
    Parse the FINAL RANKING section from the model's response.

    Args:
        ranking_text: The full text response from the model

    Returns:
        List of response labels in ranked order
    """
    import re

    # Look for "FINAL RANKING:" section
    if "FINAL RANKING:" in ranking_text:
        # Extract everything after "FINAL RANKING:"
        parts = ranking_text.split("FINAL RANKING:")
        if len(parts) >= 2:
            ranking_section = parts[1]
            # Try to extract numbered list format (e.g., "1. Response A")
            # This pattern looks for: number, period, optional space, "Response X"
            numbered_matches = re.findall(r'\d+\.\s*Response [A-Z]', ranking_section)
            if numbered_matches:
                # Extract just the "Response X" part
                return [re.search(r'Response [A-Z]', m).group() for m in numbered_matches]

            # Fallback: Extract all "Response X" patterns in order
            matches = re.findall(r'Response [A-Z]', ranking_section)
            return matches

    # Fallback: try to find any "Response X" patterns in order
    matches = re.findall(r'Response [A-Z]', ranking_text)
    return matches


def calculate_aggregate_rankings(
    stage2_results: List[Dict[str, Any]],
    label_to_model: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    Calculate aggregate rankings across all models.

    Args:
        stage2_results: Rankings from each model
        label_to_model: Mapping from anonymous labels to model names

    Returns:
        List of dicts with model name and average rank, sorted best to worst
    """
    from collections import defaultdict

    # Track positions for each model
    model_positions = defaultdict(list)

    for ranking in stage2_results:
        ranking_text = ranking['ranking']

        # Parse the ranking from the structured format
        parsed_ranking = parse_ranking_from_text(ranking_text)

        for position, label in enumerate(parsed_ranking, start=1):
            if label in label_to_model:
                model_name = label_to_model[label]
                model_positions[model_name].append(position)

    # Calculate average position for each model
    aggregate = []
    for model, positions in model_positions.items():
        if positions:
            avg_rank = sum(positions) / len(positions)
            aggregate.append({
                "model": model,
                "average_rank": round(avg_rank, 2),
                "rankings_count": len(positions)
            })

    # Sort by average rank (lower is better)
    aggregate.sort(key=lambda x: x['average_rank'])

    return aggregate


async def generate_conversation_title(user_query: str, user_id: Optional[uuid.UUID] = None, db: Optional[Any] = None) -> str:
    """
    Generate a short title for a conversation based on the first user message.

    Args:
        user_query: The first user message
        user_id: Optional user ID for user-specific API keys
        db: Optional database session for resolving API keys

    Returns:
        A short title (3-5 words)
    """
    title_prompt = f"""Generate a very short title (3-5 words maximum) that summarizes the following question.
The title should be concise and descriptive. Do not use quotes or punctuation in the title.

Question: {user_query}

Title:"""

    messages = [{"role": "user", "content": title_prompt}]

    # Use gemini-2.5-flash for title generation (fast and cheap)
    # Pass user_id and db to use user-specific API keys
    response = await query_model("google/gemini-2.5-flash", messages, timeout=30.0, user_id=user_id, db=db)

    if response is None:
        # Fallback to a generic title
        return "New Conversation"

    title = response.get('content', 'New Conversation').strip()

    # Clean up the title - remove quotes, limit length
    title = title.strip('"\'')

    # Truncate if too long
    if len(title) > 50:
        title = title[:47] + "..."

    return title


async def gather_context(user_query: str) -> Dict[str, Any]:
    """
    Gather additional context using enhanced features (web search, memory, etc.)

    Args:
        user_query: The user's question

    Returns:
        Dict with context from various sources
    """
    features = get_enhanced_features()
    context = {}

    # Web search for current information
    if features.get("web_search"):
        try:
            search_results = await web_search(user_query, num_results=3)
            if search_results and search_results[0].get("url"):
                context["web_search"] = search_results
        except Exception as e:
            print(f"Web search failed: {e}")

    # Memory context
    if features.get("memory"):
        try:
            memory_context = get_memory_context(user_query, limit=5)
            if memory_context and memory_context != "No memories stored yet.":
                context["memory"] = memory_context
        except Exception as e:
            print(f"Memory retrieval failed: {e}")

    return context


async def run_full_council(
    user_query: str,
    conversation_context: Optional[str] = None,
    conversation_id: Optional[str] = None,
    attached_files: Optional[List[str]] = None,
    project_id: Optional[str] = None,
    user_id: Optional[uuid.UUID] = None,
    db: Optional[Any] = None
) -> Tuple[List, List, Dict, Dict]:
    """
    Run the complete 3-stage council process with enhanced features.

    Args:
        user_query: The user's question
        conversation_context: Optional context from previous conversation exchanges
        project_id: Optional project ID to inject project-specific context
        conversation_id: Optional conversation ID for file access
        attached_files: Optional list of filenames attached to this query

    Returns:
        Tuple of (stage1_results, stage2_results, stage3_result, metadata)
    """
    # Gather project context if project_id provided
    project_context = None
    if project_id:
        from . import projects
        project_context = projects.get_project_context(project_id)

    # Gather additional context
    context = await gather_context(user_query)

    # Enhance the query with context if available
    enhanced_query = user_query
    context_sections = []

    # Add project context first (highest priority - defines the project scope)
    if project_context:
        context_sections.append(project_context)

    # Add attached files (most relevant to the query)
    if conversation_id and attached_files:
        from . import files
        file_context = files.format_files_for_context(conversation_id, attached_files)
        if file_context:
            context_sections.append(file_context)

    # Add conversation history context (also highly relevant)
    if conversation_context:
        context_sections.append(conversation_context)

    # Add other enhanced features
    if context:
        if context.get("web_search"):
            web_context = "**Recent Web Search Results:**\n"
            for result in context["web_search"]:
                web_context += f"- {result['title']}: {result['snippet']}\n"
            context_sections.append(web_context)

        if context.get("memory"):
            context_sections.append(f"**Relevant Memory Context:**\n{context['memory']}")

    # Combine all context sections
    if context_sections:
        all_context = "\n\n".join(context_sections)
        enhanced_query = f"{all_context}\n\n---\n\n{user_query}"

    # Stage 1: Collect individual responses (pass enhanced query with all context)
    stage1_results = await stage1_collect_responses(enhanced_query if context_sections else user_query, None, user_id=user_id, db=db)

    # If no models responded successfully, return error
    if not stage1_results:
        # #region agent log
        import os
        import json
        from datetime import datetime
        debug_log_path = os.getenv("DEBUG_LOG_PATH", "/Users/sezars/llm-council/.cursor/debug.log")
        if os.path.exists(os.path.dirname(debug_log_path)):
            try:
                with open(debug_log_path, 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"council-error","hypothesisId":"H5","location":"council.py:468","message":"all_models_failed","data":{"user_query":user_query[:100],"user_id":str(user_id) if user_id else None,"council_models_count":len(council_models) if 'council_models' in locals() else 0},"timestamp":int(datetime.now().timestamp()*1000)}) + '\n')
            except Exception:
                pass
        # #endregion
        return [], [], {
            "model": "error",
            "response": "All models failed to respond. Please check your API key in Settings → API Keys and ensure OpenRouter API key is set."
        }, {}

    # Stage 2: Collect rankings (use original query for ranking, not enhanced)
    stage2_results, label_to_model = await stage2_collect_rankings(user_query, stage1_results, user_id=user_id, db=db)

    # Calculate aggregate rankings
    aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)

    # Stage 3: Synthesize final answer
    stage3_result = await stage3_synthesize_final(
        user_query,
        stage1_results,
        stage2_results,
        user_id=user_id,
        db=db
    )

    # Remember the decision if memory is enabled
    features = get_enhanced_features()
    if features.get("memory"):
        try:
            remember_decision(
                question=user_query[:500],
                decision=stage3_result.get("response", "")[:1000],
                reasoning=f"Aggregate ranking: {aggregate_rankings[0]['model'] if aggregate_rankings else 'N/A'}"
            )
        except Exception as e:
            print(f"Failed to remember decision: {e}")

    # Prepare metadata
    metadata = {
        "label_to_model": label_to_model,
        "aggregate_rankings": aggregate_rankings,
        "context_used": {
            "web_search": bool(context.get("web_search")),
            "memory": bool(context.get("memory"))
        }
    }

    # Track analytics
    try:
        from . import analytics_tracker
        analytics_tracker.track_council_query(
            stage1_results,
            stage2_results,
            stage3_result,
            aggregate_rankings
        )
    except Exception as e:
        # Don't fail the request if analytics fails
        print(f"Analytics tracking failed: {e}")

    return stage1_results, stage2_results, stage3_result, metadata


async def run_full_council_stream(
    user_query: str,
    conversation_context: Optional[str] = None,
    user_id: Optional[uuid.UUID] = None,
    db: Optional[Any] = None
):
    """
    Run the complete 3-stage council process with streaming.
    Yields events as they occur for real-time updates.

    Args:
        user_query: The user's question
        conversation_context: Optional context from previous conversation exchanges

    Yields:
        Dict events with structure:
        - {type: 'stage1_model_start', model: str}
        - {type: 'stage1_model_chunk', model: str, chunk: str}
        - {type: 'stage1_model_complete', model: str, response: str}
        - {type: 'stage1_complete', data: List[Dict]}
        - {type: 'stage2_model_start', model: str}
        - {type: 'stage2_model_chunk', model: str, chunk: str}
        - {type: 'stage2_model_complete', model: str, response: str}
        - {type: 'stage2_complete', data: List[Dict], metadata: Dict}
        - {type: 'stage3_start'}
        - {type: 'stage3_chunk', chunk: str}
        - {type: 'stage3_complete', data: Dict}
        - {type: 'complete', stage1: List, stage2: List, stage3: Dict, metadata: Dict}
    """
    # Gather additional context
    context = await gather_context(user_query)

    # Build enhanced query with context
    enhanced_query = user_query
    context_sections = []

    if conversation_context:
        context_sections.append(conversation_context)

    if context:
        if context.get("web_search"):
            web_context = "**Recent Web Search Results:**\n"
            for result in context["web_search"]:
                web_context += f"- {result['title']}: {result['snippet']}\n"
            context_sections.append(web_context)

        if context.get("memory"):
            context_sections.append(f"**Relevant Memory Context:**\n{context['memory']}")

    if context_sections:
        all_context = "\n\n".join(context_sections)
        enhanced_query = f"{all_context}\n\n---\n\n{user_query}"

    # Stage 1: Stream individual responses from all models in parallel
    # Get user-specific council models if available
    if user_id and db:
        from .database import crud as db_crud
        settings = await db_crud.settings.get_by_user_id(db, user_id)
        if settings and settings.council_models:
            council_models = settings.council_models
        else:
            council_models = get_council_models()
    else:
        council_models = get_council_models()
    
    messages = [{"role": "user", "content": enhanced_query if context_sections else user_query}]

    stage1_results = []

    # Create async tasks for all models
    async def stream_model_stage1(model):
        """Stream a single model's response for stage 1."""
        yield {"type": "stage1_model_start", "model": model}

        full_response = ""
        async for event in query_model_stream(model, messages, user_id=user_id, db=db):
            if event.get("chunk"):
                full_response += event["chunk"]
                yield {"type": "stage1_model_chunk", "model": model, "chunk": event["chunk"]}
            elif event.get("done"):
                yield {
                    "type": "stage1_model_complete",
                    "model": model,
                    "response": full_response,
                    "usage": event.get("usage", {})
                }
            elif event.get("error"):
                yield {
                    "type": "stage1_model_error",
                    "model": model,
                    "error": event.get("message", "Unknown error")
                }

    # Stream all stage1 models in parallel
    tasks = [stream_model_stage1(model) for model in council_models]

    # Use asyncio to handle multiple streams
    async def merge_stage1_streams():
        """Merge multiple model streams and yield events."""
        queues = {model: asyncio.Queue() for model in council_models}

        async def consume_stream(model, generator):
            """Consume one model's stream and put events in queue."""
            async for event in generator:
                await queues[model].put(event)
            await queues[model].put(None)  # Signal completion

        # Start all consumers
        consumers = [asyncio.create_task(consume_stream(model, gen)) for model, gen in zip(council_models, tasks)]

        # Yield events as they arrive from any queue
        active_queues = set(council_models)
        while active_queues:
            for model in list(active_queues):
                try:
                    event = await asyncio.wait_for(queues[model].get(), timeout=0.01)
                    if event is None:
                        active_queues.remove(model)
                    else:
                        yield event
                except asyncio.TimeoutError:
                    continue

        # Wait for all consumers to finish
        await asyncio.gather(*consumers)

    # Stream stage 1
    stage1_responses = {}
    async for event in merge_stage1_streams():
        yield event
        if event.get("type") == "stage1_model_complete":
            stage1_responses[event["model"]] = event["response"]

    # Build stage1_results
    for model, response in stage1_responses.items():
        if response:
            stage1_results.append({"model": model, "response": response})

    yield {"type": "stage1_complete", "data": stage1_results}

    if not stage1_results:
        # #region agent log
        import os
        import json
        from datetime import datetime
        debug_log_path = os.getenv("DEBUG_LOG_PATH", "/Users/sezars/llm-council/.cursor/debug.log")
        if os.path.exists(os.path.dirname(debug_log_path)):
            try:
                with open(debug_log_path, 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"council-stream-error","hypothesisId":"H6","location":"council.py:667","message":"all_models_failed_stream","data":{"user_query":user_query[:100],"user_id":str(user_id) if user_id else None},"timestamp":int(datetime.now().timestamp()*1000)}) + '\n')
            except Exception:
                pass
        # #endregion
        yield {
            "type": "error",
            "message": "All models failed to respond. Please check your API key in Settings → API Keys and ensure OpenRouter API key is set."
        }
        return

    # Stage 2: Stream rankings from all models in parallel
    # Create anonymized labels
    labels = [chr(65 + i) for i in range(len(stage1_results))]
    label_to_model = {
        f"Response {label}": result['model']
        for label, result in zip(labels, stage1_results)
    }

    # Build ranking prompt
    responses_text = "\n\n".join([
        f"Response {label}:\n{result['response']}"
        for label, result in zip(labels, stage1_results)
    ])

    ranking_prompt = f"""You are evaluating different responses to the following question:

Question: {user_query}

Here are the responses from different models (anonymized):

{responses_text}

Your task:
1. First, evaluate each response individually. For each response, explain what it does well and what it does poorly.
2. Then, at the very end of your response, provide a final ranking.

IMPORTANT: Your final ranking MUST be formatted EXACTLY as follows:
- Start with the line "FINAL RANKING:" (all caps, with colon)
- Then list the responses from best to worst as a numbered list
- Each line should be: number, period, space, then ONLY the response label (e.g., "1. Response A")
- Do not add any other text or explanations in the ranking section

Example of the correct format for your ENTIRE response:

Response A provides good detail on X but misses Y...
Response B is accurate but lacks depth on Z...
Response C offers the most comprehensive answer...

FINAL RANKING:
1. Response C
2. Response A
3. Response B

Now provide your evaluation and ranking:"""

    messages_stage2 = [{"role": "user", "content": ranking_prompt}]

    stage2_results = []

    async def stream_model_stage2(model):
        """Stream a single model's ranking for stage 2."""
        yield {"type": "stage2_model_start", "model": model}

        full_ranking = ""
        async for event in query_model_stream(model, messages_stage2, user_id=user_id, db=db):
            if event.get("chunk"):
                full_ranking += event["chunk"]
                yield {"type": "stage2_model_chunk", "model": model, "chunk": event["chunk"]}
            elif event.get("done"):
                parsed = parse_ranking_from_text(full_ranking)
                yield {
                    "type": "stage2_model_complete",
                    "model": model,
                    "ranking": full_ranking,
                    "parsed_ranking": parsed,
                    "usage": event.get("usage", {})
                }
            elif event.get("error"):
                yield {
                    "type": "stage2_model_error",
                    "model": model,
                    "error": event.get("message", "Unknown error")
                }

    # Stream all stage2 models in parallel
    tasks_stage2 = [stream_model_stage2(model) for model in council_models]

    async def merge_stage2_streams():
        """Merge stage 2 streams."""
        queues = {model: asyncio.Queue() for model in council_models}

        async def consume_stream(model, generator):
            async for event in generator:
                await queues[model].put(event)
            await queues[model].put(None)

        consumers = [asyncio.create_task(consume_stream(model, gen)) for model, gen in zip(council_models, tasks_stage2)]

        active_queues = set(council_models)
        while active_queues:
            for model in list(active_queues):
                try:
                    event = await asyncio.wait_for(queues[model].get(), timeout=0.01)
                    if event is None:
                        active_queues.remove(model)
                    else:
                        yield event
                except asyncio.TimeoutError:
                    continue

        await asyncio.gather(*consumers)

    # Stream stage 2
    stage2_responses = {}
    async for event in merge_stage2_streams():
        yield event
        if event.get("type") == "stage2_model_complete":
            stage2_responses[event["model"]] = {
                "ranking": event["ranking"],
                "parsed": event["parsed_ranking"]
            }

    # Build stage2_results
    for model, data in stage2_responses.items():
        if data:
            stage2_results.append({
                "model": model,
                "ranking": data["ranking"],
                "parsed_ranking": data["parsed"]
            })

    # Calculate aggregate rankings
    aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)

    yield {
        "type": "stage2_complete",
        "data": stage2_results,
        "metadata": {
            "label_to_model": label_to_model,
            "aggregate_rankings": aggregate_rankings
        }
    }

    # Stage 3: Stream chairman synthesis
    yield {"type": "stage3_start"}

    # Build chairman prompt
    stage1_text = "\n\n".join([
        f"Model: {result['model']}\nResponse: {result['response']}"
        for result in stage1_results
    ])

    stage2_text = "\n\n".join([
        f"Model: {result['model']}\nRanking: {result['ranking']}"
        for result in stage2_results
    ])

    chairman_prompt = f"""You are the Chairman of an LLM Council. Multiple AI models have provided responses to a user's question, and then ranked each other's responses.

Original Question: {user_query}

STAGE 1 - Individual Responses:
{stage1_text}

STAGE 2 - Peer Rankings:
{stage2_text}

Your task as Chairman is to synthesize all of this information into a single, comprehensive, accurate answer to the user's original question. Consider:
- The individual responses and their insights
- The peer rankings and what they reveal about response quality
- Any patterns of agreement or disagreement

Provide a clear, well-reasoned final answer that represents the council's collective wisdom:"""

    messages_stage3 = [{"role": "user", "content": chairman_prompt}]
    
    # Get user-specific chairman model if available
    if user_id and db:
        from .database import crud as db_crud
        settings = await db_crud.settings.get_by_user_id(db, user_id)
        if settings and settings.chairman_model:
            chairman = settings.chairman_model
        else:
            chairman = get_chairman_model()
    else:
        chairman = get_chairman_model()

    full_synthesis = ""
    stage3_result = None
    async for event in query_model_stream(chairman, messages_stage3, user_id=user_id, db=db):
        if event.get("chunk"):
            full_synthesis += event["chunk"]
            yield {"type": "stage3_chunk", "chunk": event["chunk"]}
        elif event.get("done"):
            stage3_result = {
                "model": chairman,
                "response": full_synthesis
            }
            yield {
                "type": "stage3_complete",
                "data": stage3_result,
                "usage": event.get("usage", {})
            }
        elif event.get("error"):
            stage3_result = {
                "model": chairman,
                "response": "Error: Unable to generate final synthesis."
            }
            yield {"type": "stage3_complete", "data": stage3_result}

    # Remember the decision if memory is enabled
    features = get_enhanced_features()
    if features.get("memory") and stage3_result:
        try:
            remember_decision(
                question=user_query[:500],
                decision=full_synthesis[:1000],
                reasoning=f"Aggregate ranking: {aggregate_rankings[0]['model'] if aggregate_rankings else 'N/A'}"
            )
        except Exception as e:
            print(f"Failed to remember decision: {e}")

    # Final metadata
    metadata = {
        "label_to_model": label_to_model,
        "aggregate_rankings": aggregate_rankings,
        "context_used": {
            "web_search": bool(context.get("web_search")),
            "memory": bool(context.get("memory"))
        }
    }

    # Yield final complete event
    yield {
        "type": "complete",
        "stage1": stage1_results,
        "stage2": stage2_results,
        "stage3": stage3_result,
        "metadata": metadata
    }
