"""Analytics tracking for LLM Council queries."""

from typing import Dict, List, Optional
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

ANALYTICS_FILE = "backend/data/analytics.json"

# Import budgets module for cost tracking
try:
    from . import budgets
    BUDGETS_AVAILABLE = True
except ImportError:
    BUDGETS_AVAILABLE = False


def _ensure_analytics_file():
    """Ensure analytics file exists."""
    os.makedirs(os.path.dirname(ANALYTICS_FILE), exist_ok=True)
    if not os.path.exists(ANALYTICS_FILE):
        with open(ANALYTICS_FILE, 'w') as f:
            json.dump({"queries": []}, f)


def _load_analytics() -> Dict:
    """Load analytics data from file."""
    _ensure_analytics_file()
    try:
        with open(ANALYTICS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {"queries": []}


def _save_analytics(data: Dict):
    """Save analytics data to file."""
    _ensure_analytics_file()
    with open(ANALYTICS_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def record_query(
    models: List[str],
    chairman: str,
    tokens_used: Dict[str, int],
    cost: float,
    response_times: Dict[str, float],
    aggregate_rankings: Optional[List[Dict]] = None
):
    """
    Record a council query for analytics.

    Args:
        models: List of council model IDs
        chairman: Chairman model ID
        tokens_used: Dict mapping model ID to token count
        cost: Total cost in USD
        response_times: Dict mapping model ID to response time in seconds
        aggregate_rankings: Optional list of {"model": str, "avg_rank": float, "votes": int}
    """
    data = _load_analytics()

    query_record = {
        "timestamp": datetime.now().isoformat(),
        "models": models,
        "chairman": chairman,
        "tokens_used": tokens_used,
        "cost": cost,
        "response_times": response_times,
        "aggregate_rankings": aggregate_rankings or []
    }

    data["queries"].append(query_record)
    _save_analytics(data)

    # Track cost against budgets
    if BUDGETS_AVAILABLE and cost > 0:
        try:
            budgets.track_spending(cost)
        except Exception as e:
            print(f"Warning: Failed to track budget spending: {e}")


def get_model_stats() -> Dict[str, Dict]:
    """
    Get performance statistics per model.

    Returns:
        Dict mapping model ID to stats:
        {
            "model_id": {
                "usage_count": int,
                "total_tokens": int,
                "total_cost": float,
                "avg_response_time": float,
                "wins": int,  # Times ranked #1
                "avg_rank": float,  # Average ranking position (lower is better)
                "appearances": int  # Times included in rankings
            }
        }
    """
    data = _load_analytics()
    stats = defaultdict(lambda: {
        "usage_count": 0,
        "total_tokens": 0,
        "total_cost": 0.0,
        "response_times": [],
        "wins": 0,
        "rank_positions": [],
        "appearances": 0
    })

    for query in data["queries"]:
        # Track usage for all models in the query
        all_models = set(query["models"] + [query["chairman"]])

        for model in all_models:
            stats[model]["usage_count"] += 1

            # Add tokens if available
            if model in query.get("tokens_used", {}):
                stats[model]["total_tokens"] += query["tokens_used"][model]

            # Add response time if available
            if model in query.get("response_times", {}):
                stats[model]["response_times"].append(query["response_times"][model])

        # Track rankings (only for council members, not chairman)
        if query.get("aggregate_rankings"):
            for rank_data in query["aggregate_rankings"]:
                model = rank_data["model"]
                avg_rank = rank_data["avg_rank"]

                stats[model]["appearances"] += 1
                stats[model]["rank_positions"].append(avg_rank)

                # Count wins (avg_rank close to 1.0 means ranked #1 by most)
                if avg_rank <= 1.5:  # Threshold for "win"
                    stats[model]["wins"] += 1

    # Calculate total cost (simplified - just divide total cost by number of models)
    total_cost = sum(q.get("cost", 0) for q in data["queries"])
    if total_cost > 0 and len(stats) > 0:
        cost_per_model = total_cost / len(stats)
        for model in stats:
            stats[model]["total_cost"] = cost_per_model

    # Convert to final format with averages
    result = {}
    for model, data in stats.items():
        result[model] = {
            "usage_count": data["usage_count"],
            "total_tokens": data["total_tokens"],
            "total_cost": round(data["total_cost"], 4),
            "avg_response_time": round(statistics.mean(data["response_times"]), 2) if data["response_times"] else 0,
            "wins": data["wins"],
            "avg_rank": round(statistics.mean(data["rank_positions"]), 2) if data["rank_positions"] else None,
            "appearances": data["appearances"]
        }

    return result


def get_cost_breakdown() -> Dict:
    """
    Get cost breakdown by model and by day.

    Returns:
        {
            "total_cost": float,
            "by_model": {"model_id": float, ...},
            "by_day": {"2024-01-01": float, ...}
        }
    """
    data = _load_analytics()

    total_cost = sum(q.get("cost", 0) for q in data["queries"])

    # Cost by model (approximate - divide equally among models in query)
    by_model = defaultdict(float)
    for query in data["queries"]:
        cost = query.get("cost", 0)
        all_models = set(query["models"] + [query["chairman"]])
        if all_models and cost > 0:
            cost_per_model = cost / len(all_models)
            for model in all_models:
                by_model[model] += cost_per_model

    # Cost by day
    by_day = defaultdict(float)
    for query in data["queries"]:
        date = query["timestamp"].split("T")[0]  # Extract YYYY-MM-DD
        by_day[date] += query.get("cost", 0)

    return {
        "total_cost": round(total_cost, 4),
        "by_model": {k: round(v, 4) for k, v in by_model.items()},
        "by_day": dict(sorted(by_day.items()))
    }


def get_response_times() -> Dict[str, float]:
    """
    Get average response time per model.

    Returns:
        Dict mapping model ID to average response time in seconds
    """
    data = _load_analytics()

    times_by_model = defaultdict(list)
    for query in data["queries"]:
        for model, time in query.get("response_times", {}).items():
            times_by_model[model].append(time)

    return {
        model: round(statistics.mean(times), 2)
        for model, times in times_by_model.items()
        if times
    }


def get_usage_trends() -> Dict:
    """
    Get usage trends over time.

    Returns:
        {
            "queries_per_day": {"2024-01-01": int, ...},
            "queries_per_hour": {0: int, 1: int, ..., 23: int},
            "total_queries": int
        }
    """
    data = _load_analytics()

    queries_per_day = defaultdict(int)
    queries_per_hour = defaultdict(int)

    for query in data["queries"]:
        # Parse timestamp
        dt = datetime.fromisoformat(query["timestamp"])

        # Count by day
        date_str = dt.strftime("%Y-%m-%d")
        queries_per_day[date_str] += 1

        # Count by hour
        queries_per_hour[dt.hour] += 1

    return {
        "queries_per_day": dict(sorted(queries_per_day.items())),
        "queries_per_hour": dict(sorted(queries_per_hour.items())),
        "total_queries": len(data["queries"])
    }


def get_all_analytics() -> Dict:
    """
    Get comprehensive analytics summary.

    Returns complete analytics including model stats, costs, times, and trends.
    """
    return {
        "model_stats": get_model_stats(),
        "cost_breakdown": get_cost_breakdown(),
        "response_times": get_response_times(),
        "usage_trends": get_usage_trends()
    }


def clear_analytics():
    """Clear all analytics data."""
    _save_analytics({"queries": []})
