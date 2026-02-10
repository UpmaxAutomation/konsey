"""Analytics and ratings routes for LLM Council."""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_user, get_current_user_optional
from ..database.connection import get_db
from .. import analytics, ratings, storage_adapter as storage
from ..openrouter import get_session_usage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["analytics"])


# ──────────────────────────────────────────────
# Request / Response schemas
# ──────────────────────────────────────────────

class SubmitRatingRequest(BaseModel):
    conversation_id: str
    message_index: int
    model_id: str
    rating: int
    feedback_text: Optional[str] = None
    query_category: Optional[str] = None


# ──────────────────────────────────────────────
# Analytics endpoints
# ──────────────────────────────────────────────

@router.get(
    "/analytics",
    tags=["analytics"],
    summary="Get Comprehensive Analytics",
    response_description="Full analytics summary across all dimensions"
)
async def get_analytics():
    """
    Get comprehensive analytics summary.

    Returns a complete overview of system usage including model performance,
    costs, response times, and usage trends.

    Returns:
        dict: Comprehensive analytics object with:
            - model_stats: Per-model performance metrics
            - cost_breakdown: Cost analysis by model and time
            - response_times: Latency statistics
            - usage_trends: Historical usage data
    """
    return analytics.get_all_analytics()


@router.get(
    "/analytics/models",
    tags=["analytics"],
    summary="Get Model Performance Statistics",
    response_description="Per-model performance metrics"
)
async def get_analytics_models():
    """
    Get model performance statistics.

    Returns detailed metrics for each model including request counts,
    success rates, average response times, and ranking performance.

    Returns:
        dict: Model statistics with per-model metrics
    """
    return analytics.get_model_stats()


@router.get(
    "/analytics/costs",
    tags=["analytics"],
    summary="Get Cost Breakdown",
    response_description="Cost analysis by model and time period"
)
async def get_analytics_costs():
    """
    Get cost breakdown.

    Returns cost analysis including total spend, per-model costs,
    and cost trends over time.

    Returns:
        dict: Cost breakdown with per-model and temporal analysis
    """
    return analytics.get_cost_breakdown()


@router.get(
    "/analytics/times",
    tags=["analytics"],
    summary="Get Response Time Statistics",
    response_description="Latency metrics and percentiles"
)
async def get_analytics_times():
    """
    Get response time statistics.

    Returns latency analysis including average, median, p95, and p99
    response times for each model and overall.

    Returns:
        dict: Response time statistics with percentiles
    """
    return analytics.get_response_times()


@router.get(
    "/analytics/trends",
    tags=["analytics"],
    summary="Get Usage Trends",
    response_description="Historical usage data over time"
)
async def get_analytics_trends():
    """
    Get usage trends over time.

    Returns historical data showing usage patterns, including
    daily/weekly/monthly request volumes and cost trends.

    Returns:
        dict: Usage trends with temporal breakdown
    """
    return analytics.get_usage_trends()


@router.post(
    "/analytics/clear",
    tags=["analytics"],
    summary="Clear Analytics Data",
    response_description="Confirmation of analytics clear"
)
async def clear_analytics_data():
    """
    Clear all analytics data.

    Removes all historical analytics data including model stats,
    costs, response times, and trends. Use with caution.

    Returns:
        dict: Confirmation with status "cleared"
    """
    analytics.clear_analytics()
    return {"status": "cleared"}


# ──────────────────────────────────────────────
# Ratings endpoints
# ──────────────────────────────────────────────

@router.post(
    "/ratings",
    tags=["ratings"],
    summary="Submit Response Rating",
    response_description="Confirmation of rating submission"
)
async def submit_response_rating(request: SubmitRatingRequest):
    """
    Submit a rating for a model response.

    Rate individual model responses on a scale (typically 1-5) to help
    improve model recommendations and track quality over time.

    Args:
        request: SubmitRatingRequest containing:
            - conversation_id: The conversation containing the response
            - message_index: Index of the message in the conversation
            - model_id: The model being rated
            - rating: Numeric rating (1-5)
            - feedback_text: Optional written feedback
            - query_category: Optional category for analytics

    Returns:
        dict: Confirmation with status and rating_saved flag

    Raises:
        HTTPException 400: If rating value is invalid
        HTTPException 500: If rating submission fails
    """
    try:
        success = ratings.submit_rating(
            conversation_id=request.conversation_id,
            message_index=request.message_index,
            model_id=request.model_id,
            rating=request.rating,
            feedback_text=request.feedback_text,
            query_category=request.query_category
        )
        return {"status": "success", "rating_saved": success}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit rating: {str(e)}")


@router.get(
    "/ratings/{conversation_id}/{message_index}/{model_id}",
    tags=["ratings"],
    summary="Get Response Rating",
    response_description="Rating data if exists"
)
async def get_response_rating(conversation_id: str, message_index: int, model_id: str):
    """
    Get existing rating for a specific response.

    Check if a rating exists for a particular model response in a conversation.

    Args:
        conversation_id: The conversation ID
        message_index: Index of the message
        model_id: The model to check rating for

    Returns:
        dict: Object with has_rating flag and rating data if exists
    """
    rating = ratings.get_rating(conversation_id, message_index, model_id)
    if rating is None:
        return {"has_rating": False}
    return {"has_rating": True, "rating": rating}


@router.get(
    "/ratings/models",
    tags=["ratings"],
    summary="Get Model Rating Statistics",
    response_description="Aggregate rating statistics per model"
)
async def get_model_ratings():
    """
    Get rating statistics for all models.

    Returns aggregate metrics including average rating, total ratings,
    and rating distribution for each model.

    Returns:
        dict: Per-model rating statistics
    """
    return ratings.get_model_rating_stats()


@router.get(
    "/ratings/recommendations",
    tags=["ratings"],
    summary="Get Model Recommendations",
    response_description="Recommended models based on query and ratings"
)
async def get_rating_recommendations(query: str, num_recommendations: int = 3):
    """
    Get model recommendations based on query and past ratings.

    Uses historical rating data and query analysis to suggest
    the best models for a given type of question.

    Args:
        query: The query to get recommendations for
        num_recommendations: Number of models to recommend (default: 3)

    Returns:
        dict: Query and list of recommended model IDs with scores
    """
    recommendations = ratings.get_recommendations_for_query(query, num_recommendations)
    return {"query": query, "recommendations": recommendations}


@router.get(
    "/ratings/analytics",
    tags=["ratings"],
    summary="Get Rating Analytics",
    response_description="Comprehensive rating analytics"
)
async def get_rating_analytics_summary():
    """
    Get comprehensive rating analytics.

    Returns detailed analytics including rating trends, category breakdowns,
    model comparisons, and quality metrics over time.

    Returns:
        dict: Comprehensive rating analytics
    """
    return ratings.get_rating_analytics()


@router.post(
    "/ratings/clear",
    tags=["ratings"],
    summary="Clear All Ratings",
    response_description="Confirmation of ratings clear"
)
async def clear_all_ratings():
    """
    Clear all rating data.

    Removes all historical rating data. Use with caution as this
    affects model recommendations.

    Returns:
        dict: Confirmation with status "cleared"
    """
    ratings.clear_ratings()
    return {"status": "cleared"}


# ──────────────────────────────────────────────
# Enhanced analytics endpoints (v2)
# ──────────────────────────────────────────────

@router.get(
    "/analytics/overview",
    tags=["analytics"],
    summary="Get Analytics Overview",
    response_description="Comprehensive usage analytics summary"
)
async def get_analytics_overview():
    """
    Get comprehensive usage analytics overview.

    Returns aggregated usage statistics including conversation counts,
    token usage, costs, and trends.

    Returns:
        dict: Analytics overview containing:
            - overview: Total conversations, messages, tokens, and cost
            - by_model: Per-model token usage and costs
            - trends: Today's activity and active model count
            - generated_at: Timestamp of analytics generation
    """
    conversations = await storage.list_conversations()
    total_conversations = len(conversations)
    total_messages = sum(c.get("message_count", 0) for c in conversations)

    # Model usage from session
    usage = get_session_usage()

    # Calculate costs and trends
    model_costs = {}
    for model, data in usage.get("by_model", {}).items():
        cost = (data.get("input_tokens", 0) * 0.000003 +
                data.get("output_tokens", 0) * 0.000015)
        model_costs[model] = {
            "tokens": data.get("input_tokens", 0) + data.get("output_tokens", 0),
            "cost": round(cost, 4)
        }

    return {
        "overview": {
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "total_tokens": usage.get("total_tokens", 0),
            "total_cost": round(sum(m["cost"] for m in model_costs.values()), 4)
        },
        "by_model": model_costs,
        "trends": {
            "conversations_today": len([c for c in conversations
                if c.get("created_at", "").startswith(datetime.now().strftime("%Y-%m-%d"))]),
            "messages_today": 0,  # Would calculate from actual data
            "active_models": len(model_costs)
        },
        "generated_at": datetime.now().isoformat()
    }


@router.get(
    "/analytics/v2/models",
    tags=["analytics"],
    summary="Get Model Analytics",
    response_description="Detailed per-model usage statistics"
)
async def get_model_analytics():
    """
    Get detailed per-model analytics.

    Returns usage statistics broken down by model including token counts,
    costs, response times, and success rates.

    Returns:
        dict: Model analytics containing:
            - models: List of per-model statistics sorted by usage
            - count: Number of models with usage data
    """
    usage = get_session_usage()
    by_model = usage.get("by_model", {})

    models_data = []
    for model, data in by_model.items():
        input_tokens = data.get("input_tokens", 0)
        output_tokens = data.get("output_tokens", 0)
        cost = input_tokens * 0.000003 + output_tokens * 0.000015

        models_data.append({
            "model": model,
            "requests": data.get("requests", 0),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost": round(cost, 4),
            "avg_response_time": data.get("avg_response_time", 0),
            "success_rate": data.get("success_rate", 100)
        })

    # Sort by usage
    models_data.sort(key=lambda x: x["total_tokens"], reverse=True)

    return {"models": models_data, "count": len(models_data)}


@router.get(
    "/analytics/conversations",
    tags=["analytics"],
    summary="Get Conversation Analytics",
    response_description="Conversation-level usage statistics"
)
async def get_conversation_analytics():
    """
    Get conversation-level analytics.

    Returns statistics about conversation patterns including daily
    counts and average messages per conversation.

    Returns:
        dict: Conversation analytics containing:
            - total: Total number of conversations
            - daily: Per-day conversation and message counts (last 30 days)
            - avg_messages_per_conversation: Average message count
    """
    conversations = await storage.list_conversations()

    # Group by date
    by_date = {}
    for conv in conversations:
        date = conv.get("created_at", "")[:10]
        if date not in by_date:
            by_date[date] = {"count": 0, "messages": 0}
        by_date[date]["count"] += 1
        by_date[date]["messages"] += conv.get("message_count", 0)

    # Convert to list and sort
    daily_data = [
        {"date": date, **data}
        for date, data in sorted(by_date.items(), reverse=True)
    ][:30]  # Last 30 days

    return {
        "total": len(conversations),
        "daily": daily_data,
        "avg_messages_per_conversation": (
            sum(c.get("message_count", 0) for c in conversations) / len(conversations)
            if conversations else 0
        )
    }


@router.get(
    "/analytics/export",
    tags=["analytics"],
    summary="Export Analytics",
    response_description="Full analytics data export"
)
async def export_analytics():
    """
    Export full analytics data as JSON.

    Combines all analytics endpoints into a single comprehensive export
    suitable for backup or external analysis.

    Returns:
        dict: Complete analytics export containing:
            - overview: Summary analytics
            - models: Per-model analytics
            - conversations: Conversation analytics
            - exported_at: Export timestamp
    """
    overview = await get_analytics_overview()
    models = await get_model_analytics()
    conversations = await get_conversation_analytics()

    return {
        "overview": overview,
        "models": models,
        "conversations": conversations,
        "exported_at": datetime.now().isoformat()
    }
