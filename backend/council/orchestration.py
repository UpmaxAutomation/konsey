"""Main council orchestration - run_full_council and run_full_council_stream."""

import logging
import asyncio
import uuid
from typing import List, Dict, Any, Tuple, Optional

from .stage1 import stage1_collect_responses
from .stage2 import stage2_collect_rankings
from .stage3 import stage3_synthesize_final
from .aggregation import calculate_aggregate_rankings
from .context import gather_context, format_web_context
from .parsing import parse_ranking_from_text

logger = logging.getLogger(__name__)


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
        web_search: Enable web search
        deep_search: Enable deep search
        user_id: User ID for API key resolution
        db: Database session

    Returns:
        Tuple of (stage1_results, stage2_results, stage3_result, metadata)
    """
    from ..config import get_enhanced_features
    from ..tools import remember_decision

    # Gather project context if project_id provided
    project_context = None
    if project_id:
        from .. import projects
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
        from .. import files
        # Separate image files from text files
        image_files = [f for f in attached_files if files.is_image_file(f)]
        text_files = [f for f in attached_files if not files.is_image_file(f)]

        # Add text files to context (works with all models)
        # Pass user_query for relevance-based file ranking
        if text_files:
            file_context = files.format_files_for_context(conversation_id, text_files, query=user_query)
            if file_context:
                context_sections.append(file_context)

        # Prepare image content for vision models (will be handled separately)
        if image_files:
            image_content = files.format_files_for_vision(
                conversation_id, image_files, query=user_query
            )

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
            "response": "All models failed to respond. Please check your API key in Settings -> API Keys and ensure OpenRouter API key is set."
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
        from .. import analytics_tracker
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
    attached_files: Optional[List[str]] = None,
    project_id: Optional[str] = None
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
        conversation_id: Optional conversation ID for file access
        attached_files: Optional list of filenames attached to this query
        project_id: Optional project ID to inject project-specific context

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
    from ..config import get_council_models, get_chairman_model, get_model_persona, supports_vision, get_enhanced_features
    from ..openrouter import query_model_stream
    from ..tools import remember_decision

    # Gather project context if project_id provided
    project_context = None
    if project_id:
        from .. import projects
        project_context = projects.get_project_context(project_id)

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

    # Add project context first (highest priority - defines the project scope)
    if project_context:
        context_sections.append(project_context)

    # Handle attached files (images and text files)
    image_content = []
    if conversation_id and attached_files:
        from .. import files
        # Separate image files from text files
        image_files = [f for f in attached_files if files.is_image_file(f)]
        text_files = [f for f in attached_files if not files.is_image_file(f)]

        # Add text files to context (works with all models)
        # Pass user_query for relevance-based file ranking
        if text_files:
            try:
                file_context = files.format_files_for_context(
                    conversation_id, text_files, query=user_query
                )
                if file_context:
                    context_sections.append(file_context)
            except Exception as e:
                logger.error(f"Error formatting text files: {e}")

        # Prepare image content for vision models (will be handled separately)
        if image_files:
            try:
                image_content = files.format_files_for_vision(
                    conversation_id, image_files, query=user_query
                )
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
        from ..database import crud as db_crud
        settings = await db_crud.settings.get_by_user_id(db, user_id)
        if settings and settings.council_models:
            council_models = settings.council_models
        else:
            council_models = get_council_models()
    else:
        council_models = get_council_models()

    # Build per-model messages (for vision model support)
    final_query = enhanced_query if context_sections else user_query

    async def run_stage1(models_to_use, results_out):
        messages_by_model = {}
        for model in models_to_use:
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
        tasks = [stream_model_stage1(model) for model in models_to_use]

        # Use asyncio to handle multiple streams
        async def merge_stage1_streams():
            """Merge multiple model streams and yield events."""
            queues = {model: asyncio.Queue() for model in models_to_use}

            async def consume_stream(model, generator):
                """Consume one model's stream and put events in queue."""
                async for event in generator:
                    await queues[model].put(event)
                await queues[model].put(None)  # Signal completion

            # Start all consumers
            consumers = [asyncio.create_task(consume_stream(model, gen)) for model, gen in zip(models_to_use, tasks)]

            # Yield events as they arrive from any queue
            active_queues = set(models_to_use)
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
                results_out.append({"model": model, "response": response})

    stage1_results = []
    async for event in run_stage1(council_models, stage1_results):
        yield event

    yield {"type": "stage1_complete", "data": stage1_results}

    if not stage1_results:
        yield {
            "type": "error",
            "message": "All selected models failed to respond. Please choose different models or add a BYOK key for those providers."
        }
        return

    # Fast mode: Skip Stage 2 and go directly to Stage 3
    logger.info(f"Fast mode check: fast_mode={fast_mode}, type={type(fast_mode)}")
    if fast_mode:
        logger.info("Fast mode enabled - skipping Stage 2 peer review")

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
            from ..database import crud as db_crud
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
                "response": f"Error: No response from chairman model ({chairman}). Check API key in Settings -> API Keys."
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
    logger.info("RUNNING STAGE 2 - fast_mode was False or not set!")
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
                "ranking": event.get("ranking", ""),
                "parsed_ranking": event.get("parsed_ranking", [])
            }

    # Build stage2_results
    for model, data in stage2_responses.items():
        if data:
            stage2_results.append({
                "model": model,
                "ranking": data["ranking"],
                "parsed_ranking": data["parsed_ranking"]
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
        from ..database import crud as db_crud
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
