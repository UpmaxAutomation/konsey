"""3-stage LLM Council orchestration."""

import logging
from typing import List, Dict, Any, Tuple, Optional
import asyncio
import uuid

logger = logging.getLogger(__name__)
from .openrouter import query_models_parallel, query_model, query_model_stream
from .config import (
    get_council_models,
    get_chairman_model,
    AVAILABLE_MODELS,
    get_enhanced_features,
    get_model_persona,
    get_perplexity_api_key,
    get_perplexity_models
)
from .tools import (
    web_search,
    perplexity_search,
    execute_python,
    get_memory_context,
    remember_decision
)


def format_web_context(
    results: List[Dict[str, Any]],
    summary: Optional[str] = None
) -> str:
    """Format web search results and summary for prompt context."""
    if not results and not summary:
        return ""

    lines = ["**Web Context (Citations):**"]
    for result in results:
        title = result.get("title", "").strip()
        url = result.get("url", "").strip()
        snippet = result.get("snippet", "").strip()
        if title and url:
            lines.append(f"- {title} ({url}): {snippet}")
        elif url:
            lines.append(f"- {url}: {snippet}")
        elif title:
            lines.append(f"- {title}: {snippet}")
        else:
            lines.append(f"- {snippet}")

    if summary:
        lines.append("")
        lines.append("**Deep Search Summary:**")
        lines.append(summary.strip())

    return "\n".join(lines)


async def stage1_collect_responses(
    user_query: str,
    context: Optional[str] = None,
    image_content: Optional[List[Dict]] = None,
    user_id: Optional[uuid.UUID] = None,
    db: Optional[Any] = None
) -> List[Dict[str, Any]]:
    """
    Stage 1: Collect individual responses from all council models.

    Args:
        user_query: The user's question
        context: Optional conversation context from previous exchanges
        image_content: Optional list of image content dicts for vision models
        user_id: Optional user ID for user-specific API keys
        db: Optional database session for resolving API keys

    Returns:
        List of dicts with 'model' and 'response' keys
    """
    from .config import supports_vision

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

        # Build user content - multimodal for vision models with images
        if image_content and supports_vision(model):
            # Build multimodal content array for vision models
            user_content = [{"type": "text", "text": enhanced_query}]
            for img in image_content:
                if img.get("type") == "image":
                    # Convert to OpenAI-compatible format
                    source = img.get("source", {})
                    if source.get("type") == "base64":
                        user_content.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{source.get('media_type', 'image/png')};base64,{source.get('data', '')}"
                            }
                        })
        else:
            # Plain text content for non-vision models or no images
            user_content = enhanced_query

        if persona:
            # Prepend system message with persona
            messages_by_model[model] = [
                {"role": "system", "content": persona},
                {"role": "user", "content": user_content}
            ]
        else:
            # No persona, just user message
            messages_by_model[model] = [{"role": "user", "content": user_content}]

    # Query all models in parallel (with user-specific API keys)
    responses = await query_models_parallel(council_models, messages_by_model, user_id=user_id, db=db)

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

    return stage1_results


async def stage2_collect_rankings(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    web_context: Optional[str] = None,
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

    if web_context:
        ranking_prompt = f"{web_context}\n\n---\n\n{ranking_prompt}"

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
    web_context: Optional[str] = None,
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

    if web_context:
        chairman_prompt = f"{web_context}\n\n---\n\n{chairman_prompt}"

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
        logger.error(f"Chairman model failed: {chairman}. Check API key in Settings → API Keys.")
        return {
            "model": chairman,
            "response": f"Error: Chairman model ({chairman}) failed to respond. Please check your API key in Settings → API Keys."
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

    # Try multiple models for title generation (fast and cheap options)
    title_models = [
        "google/gemini-2.0-flash-001",
        "google/gemini-2.5-flash",
        "openai/gpt-4o-mini",
        "anthropic/claude-3-5-haiku-20241022"
    ]

    response = None
    for model in title_models:
        try:
            response = await query_model(model, messages, timeout=30.0, user_id=user_id, db=db)
            if response and response.get('content'):
                break
        except Exception as e:
            print(f"Title generation with {model} failed: {e}")
            continue

    if response is None or not response.get('content'):
        # Local fallback: extract first few words from query
        words = user_query.split()[:6]
        fallback_title = ' '.join(words)
        if len(fallback_title) > 40:
            fallback_title = fallback_title[:37] + "..."
        return fallback_title if fallback_title else "New Conversation"

    title = response.get('content', 'New Conversation').strip()

    # Clean up the title - remove quotes, limit length
    title = title.strip('"\'')

    # Truncate if too long
    if len(title) > 50:
        title = title[:47] + "..."

    return title


async def gather_context(
    user_query: str,
    web_search: Optional[bool] = None,
    deep_search: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Gather additional context using enhanced features (web search, memory, etc.)

    Args:
        user_query: The user's question

    Returns:
        Dict with context from various sources
    """
    features = get_enhanced_features()
    if web_search is not None:
        features["web_search"] = web_search
    if deep_search is not None:
        features["deep_search"] = deep_search
    context = {}

    # Web search for current information
    use_web_search = bool(features.get("web_search"))
    use_deep_search = bool(features.get("deep_search"))
    if use_web_search or use_deep_search:
        try:
            perplexity_key = get_perplexity_api_key()
            if perplexity_key:
                models = get_perplexity_models()
                model = models["deep_search"] if use_deep_search else models["search"]
                logger.info(f"Using Perplexity search: model={model}, deep_search={use_deep_search}")
                search_payload = await perplexity_search(
                    user_query,
                    api_key=perplexity_key,
                    model=model,
                    num_results=3,
                    deep_search=use_deep_search
                )
                if search_payload.get("results"):
                    context["web_search"] = search_payload["results"]
                if search_payload.get("summary"):
                    context["web_search_summary"] = search_payload["summary"]
                if search_payload.get("citations"):
                    context["web_search_citations"] = search_payload["citations"]
                logger.info(f"Perplexity search completed: {len(context.get('web_search', []))} results")
            elif use_web_search:
                logger.info("No Perplexity key, falling back to DuckDuckGo search")
                search_results = await web_search(user_query, num_results=3)
                if search_results and search_results[0].get("url"):
                    context["web_search"] = search_results
            else:
                logger.warning("Deep search requested but no Perplexity API key configured")
        except Exception as e:
            logger.error(f"Web search failed: {e}", exc_info=True)

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
    web_search: Optional[bool] = None,
    deep_search: Optional[bool] = None,
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
    context = await gather_context(
        user_query,
        web_search=web_search,
        deep_search=deep_search
    )

    # Enhance the query with context if available
    enhanced_query = user_query
    context_sections = []

    # Add project context first (highest priority - defines the project scope)
    if project_context:
        context_sections.append(project_context)

    # Add attached files (most relevant to the query)
    # Separate images for vision models vs text files for all models
    image_content = []
    if conversation_id and attached_files:
        from . import files
        # Separate image files from text files
        image_files = [f for f in attached_files if files.is_image_file(f)]
        text_files = [f for f in attached_files if not files.is_image_file(f)]

        # Add text files to context (works with all models)
        if text_files:
            file_context = files.format_files_for_context(conversation_id, text_files)
            if file_context:
                context_sections.append(file_context)

        # Prepare image content for vision models (will be handled separately)
        if image_files:
            image_content = files.format_files_for_vision(conversation_id, image_files)

    # Add conversation history context (also highly relevant)
    if conversation_context:
        context_sections.append(conversation_context)

    # Add other enhanced features
    web_context_text = ""
    if context:
        if context.get("web_search") or context.get("web_search_summary"):
            web_context_text = format_web_context(
                context.get("web_search", []),
                context.get("web_search_summary")
            )
            if web_context_text:
                context_sections.append(web_context_text)

        if context.get("memory"):
            context_sections.append(f"**Relevant Memory Context:**\n{context['memory']}")

    # Combine all context sections
    if context_sections:
        all_context = "\n\n".join(context_sections)
        enhanced_query = f"{all_context}\n\n---\n\n{user_query}"

    # Stage 1: Collect individual responses (pass enhanced query with all context)
    stage1_results = await stage1_collect_responses(
        enhanced_query if context_sections else user_query,
        None,
        image_content=image_content,
        user_id=user_id,
        db=db
    )

    # If no models responded successfully, return error
    if not stage1_results:
        return [], [], {
            "model": "error",
            "response": "All models failed to respond. Please check your API key in Settings → API Keys and ensure OpenRouter API key is set."
        }, {}

    # Stage 2: Collect rankings (use original query for ranking, not enhanced)
    stage2_results, label_to_model = await stage2_collect_rankings(
        user_query,
        stage1_results,
        web_context=web_context_text or None,
        user_id=user_id,
        db=db
    )

    # Calculate aggregate rankings
    aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)

    # Stage 3: Synthesize final answer
    stage3_result = await stage3_synthesize_final(
        user_query,
        stage1_results,
        stage2_results,
        web_context=web_context_text or None,
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
            "deep_search": bool(context.get("web_search_summary")),
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
    web_search: Optional[bool] = None,
    deep_search: Optional[bool] = None,
    user_id: Optional[uuid.UUID] = None,
    db: Optional[Any] = None,
    fast_mode: Optional[bool] = False,
    conversation_id: Optional[str] = None,
    attached_files: Optional[List[str]] = None
):
    """
    Run the complete 3-stage council process with streaming.
    Yields events as they occur for real-time updates.

    Args:
        user_query: The user's question
        conversation_context: Optional context from previous conversation exchanges
        web_search: Enable web search for context
        deep_search: Enable deep search for context
        user_id: User ID for API key resolution
        db: Database session
        fast_mode: If True, skips Stage 2 peer review for faster results

    Yields:
        Dict events with structure:
        - {type: 'context_start', search_type: str} (when gathering context)
        - {type: 'context_complete', search_type: str, success: bool}
        - {type: 'stage1_model_start', model: str}
        - {type: 'stage1_model_chunk', model: str, chunk: str}
        - {type: 'stage1_model_complete', model: str, response: str}
        - {type: 'stage1_complete', data: List[Dict]}
        - {type: 'stage2_model_start', model: str} (skipped in fast_mode)
        - {type: 'stage2_model_chunk', model: str, chunk: str} (skipped in fast_mode)
        - {type: 'stage2_model_complete', model: str, response: str} (skipped in fast_mode)
        - {type: 'stage2_complete', data: List[Dict], metadata: Dict}
        - {type: 'stage3_start'}
        - {type: 'stage3_chunk', chunk: str}
        - {type: 'stage3_complete', data: Dict}
        - {type: 'complete', stage1: List, stage2: List, stage3: Dict, metadata: Dict}
    """
    # Gather additional context (search + memory)
    context = {}

    # Only gather context if search is enabled
    if web_search or deep_search:
        search_type = "deep_search" if deep_search else "web_search"
        yield {"type": "context_start", "search_type": search_type}
        try:
            context = await gather_context(user_query, web_search=web_search, deep_search=deep_search)
            has_results = bool(context.get("web_search") or context.get("web_search_summary"))
            yield {"type": "context_complete", "search_type": search_type, "success": has_results}
        except Exception as e:
            logger.error(f"Context gathering failed: {e}")
            yield {"type": "context_complete", "search_type": search_type, "success": False, "error": str(e)}

    # Build enhanced query with context
    enhanced_query = user_query
    context_sections = []

    # Handle attached files (images and text files)
    image_content = []
    if conversation_id and attached_files:
        from . import files
        # Separate image files from text files
        image_files = [f for f in attached_files if files.is_image_file(f)]
        text_files = [f for f in attached_files if not files.is_image_file(f)]

        # Add text files to context (works with all models)
        if text_files:
            try:
                file_context = files.format_files_for_context(conversation_id, text_files)
                if file_context:
                    context_sections.append(file_context)
            except Exception as e:
                logger.error(f"Error formatting text files: {e}")

        # Prepare image content for vision models (will be handled separately)
        if image_files:
            try:
                image_content = files.format_files_for_vision(conversation_id, image_files)
                logger.info(f"Prepared {len(image_content)} images for vision models")
            except Exception as e:
                logger.error(f"Error formatting images: {e}")

    if conversation_context:
        context_sections.append(conversation_context)

    web_context_text = ""
    if context:
        if context.get("web_search") or context.get("web_search_summary"):
            web_context_text = format_web_context(
                context.get("web_search", []),
                context.get("web_search_summary")
            )
            if web_context_text:
                context_sections.append(web_context_text)

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

    # Build per-model messages (for vision model support)
    from .config import supports_vision
    final_query = enhanced_query if context_sections else user_query
    messages_by_model = {}

    for model in council_models:
        persona = get_model_persona(model)

        # Build user content - multimodal for vision models with images
        if image_content and supports_vision(model):
            # Build multimodal content array for vision models
            user_content = [{"type": "text", "text": final_query}]
            for img in image_content:
                if img.get("type") == "image":
                    source = img.get("source", {})
                    if source.get("type") == "base64":
                        user_content.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{source.get('media_type', 'image/png')};base64,{source.get('data', '')}"
                            }
                        })
        else:
            # Plain text content for non-vision models or no images
            user_content = final_query

        if persona:
            messages_by_model[model] = [
                {"role": "system", "content": persona},
                {"role": "user", "content": user_content}
            ]
        else:
            messages_by_model[model] = [{"role": "user", "content": user_content}]

    stage1_results = []

    # Create async tasks for all models
    async def stream_model_stage1(model):
        """Stream a single model's response for stage 1."""
        yield {"type": "stage1_model_start", "model": model}

        full_response = ""
        model_messages = messages_by_model[model]
        async for event in query_model_stream(model, model_messages, user_id=user_id, db=db):
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
        yield {
            "type": "error",
            "message": "All models failed to respond. Please check your API key in Settings → API Keys and ensure OpenRouter API key is set."
        }
        return

    # Fast mode: Skip Stage 2 and go directly to Stage 3
    logger.info(f"🔍 Fast mode check: fast_mode={fast_mode}, type={type(fast_mode)}")
    if fast_mode:
        logger.info("✅ Fast mode enabled - skipping Stage 2 peer review")

        # Create empty stage2 data
        stage2_results = []
        label_to_model = {}
        aggregate_rankings = []

        yield {
            "type": "stage2_complete",
            "data": stage2_results,
            "metadata": {
                "label_to_model": label_to_model,
                "aggregate_rankings": aggregate_rankings,
                "fast_mode": True
            }
        }

        # Jump to Stage 3 with fast mode prompt
        yield {"type": "stage3_start"}

        # Build simplified chairman prompt for fast mode
        stage1_text = "\n\n".join([
            f"Model: {result['model']}\nResponse: {result['response']}"
            for result in stage1_results
        ])

        chairman_prompt = f"""You are the Chairman of an LLM Council. Multiple AI models have provided responses to a user's question.

Original Question: {user_query}

Individual Responses:
{stage1_text}

Your task is to synthesize all responses into a single, comprehensive, accurate answer. Consider the strengths of each response and provide a clear final answer that represents the best insights from all models:"""

        if web_context_text:
            chairman_prompt = f"{web_context_text}\n\n---\n\n{chairman_prompt}"

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

        logger.info(f"Fast mode: Starting chairman synthesis with model: {chairman}")
        full_synthesis = ""
        stage3_result = None
        event_count = 0
        async for event in query_model_stream(chairman, messages_stage3, user_id=user_id, db=db):
            event_count += 1
            logger.debug(f"Fast mode chairman event {event_count}: {list(event.keys())}")
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
                error_msg = event.get("message", "Unknown error")
                logger.error(f"Fast mode chairman synthesis error: {error_msg}, full event: {event}")
                stage3_result = {
                    "model": chairman,
                    "response": f"Error: {error_msg}"
                }
                yield {"type": "stage3_complete", "data": stage3_result}

        # If stage3_result is still None (no events received), set error
        if stage3_result is None:
            logger.error(f"Fast mode: No response received from chairman after {event_count} events")
            stage3_result = {
                "model": chairman,
                "response": f"Error: No response from chairman model ({chairman}). Check API key in Settings → API Keys."
            }
            yield {"type": "stage3_complete", "data": stage3_result}

        # Final complete event
        yield {
            "type": "complete",
            "stage1": stage1_results,
            "stage2": stage2_results,
            "stage3": stage3_result,
            "metadata": {
                "label_to_model": label_to_model,
                "aggregate_rankings": aggregate_rankings,
                "fast_mode": True
            }
        }
        return

    # Stage 2: Stream rankings from all models in parallel
    logger.info("⚠️ RUNNING STAGE 2 - fast_mode was False or not set!")
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

    if web_context_text:
        ranking_prompt = f"{web_context_text}\n\n---\n\n{ranking_prompt}"

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

    if web_context_text:
        chairman_prompt = f"{web_context_text}\n\n---\n\n{chairman_prompt}"

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
            error_msg = event.get("message", "Unknown error")
            logger.error(f"Chairman synthesis error: {error_msg}, chairman: {chairman}")
            stage3_result = {
                "model": chairman,
                "response": f"Error: {error_msg}"
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
            "deep_search": bool(context.get("web_search_summary")),
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
