"""Response quality rating system for LLM Council."""

from typing import Dict, List, Optional, Any
import json
import os
from datetime import datetime
from collections import defaultdict
import statistics

RATINGS_FILE = "data/ratings.json"


def _ensure_ratings_file():
    """Ensure ratings file exists."""
    os.makedirs(os.path.dirname(RATINGS_FILE), exist_ok=True)
    if not os.path.exists(RATINGS_FILE):
        with open(RATINGS_FILE, 'w') as f:
            json.dump({"ratings": []}, f)


def _load_ratings() -> Dict:
    """Load ratings data from file."""
    _ensure_ratings_file()
    try:
        with open(RATINGS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {"ratings": []}


def _save_ratings(data: Dict):
    """Save ratings data to file."""
    _ensure_ratings_file()
    with open(RATINGS_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def submit_rating(
    conversation_id: str,
    message_index: int,
    model_id: str,
    rating: int,
    feedback_text: Optional[str] = None,
    query_category: Optional[str] = None
) -> bool:
    """
    Submit a rating for a model's response.

    Args:
        conversation_id: The conversation ID
        message_index: Index of the message in conversation
        model_id: Model that generated the response
        rating: Rating from 1-5 stars
        feedback_text: Optional text feedback
        query_category: Optional category (e.g., "code", "creative", "research")

    Returns:
        True if rating was saved successfully
    """
    if not (1 <= rating <= 5):
        raise ValueError("Rating must be between 1 and 5")

    data = _load_ratings()

    # Check if rating already exists for this response
    existing_idx = None
    for idx, r in enumerate(data["ratings"]):
        if (r["conversation_id"] == conversation_id and
            r["message_index"] == message_index and
            r["model_id"] == model_id):
            existing_idx = idx
            break

    rating_record = {
        "conversation_id": conversation_id,
        "message_index": message_index,
        "model_id": model_id,
        "rating": rating,
        "feedback_text": feedback_text or "",
        "query_category": query_category or "general",
        "timestamp": datetime.now().isoformat()
    }

    if existing_idx is not None:
        # Update existing rating
        data["ratings"][existing_idx] = rating_record
    else:
        # Add new rating
        data["ratings"].append(rating_record)

    _save_ratings(data)
    return True


def get_rating(conversation_id: str, message_index: int, model_id: str) -> Optional[Dict]:
    """
    Get existing rating for a specific response.

    Returns:
        Rating dict if found, None otherwise
    """
    data = _load_ratings()
    for rating in data["ratings"]:
        if (rating["conversation_id"] == conversation_id and
            rating["message_index"] == message_index and
            rating["model_id"] == model_id):
            return rating
    return None


def get_model_rating_stats() -> Dict[str, Dict]:
    """
    Get rating statistics per model.

    Returns:
        Dict mapping model ID to rating stats:
        {
            "model_id": {
                "average_rating": float,
                "total_ratings": int,
                "rating_distribution": {1: int, 2: int, 3: int, 4: int, 5: int},
                "win_rate": float,  # Percentage of 5-star ratings
                "recent_trend": str,  # "improving", "declining", "stable"
                "best_categories": List[str],  # Categories where model excels
                "feedback_summary": {
                    "positive_count": int,
                    "negative_count": int,
                    "common_themes": List[str]
                }
            }
        }
    """
    data = _load_ratings()
    stats = defaultdict(lambda: {
        "ratings": [],
        "rating_distribution": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
        "categories": defaultdict(list),
        "feedback": [],
        "timestamps": []
    })

    for rating in data["ratings"]:
        model = rating["model_id"]
        rating_value = rating["rating"]

        stats[model]["ratings"].append(rating_value)
        stats[model]["rating_distribution"][rating_value] += 1
        stats[model]["categories"][rating["query_category"]].append(rating_value)
        stats[model]["timestamps"].append(rating["timestamp"])

        if rating["feedback_text"]:
            stats[model]["feedback"].append(rating["feedback_text"])

    # Calculate final statistics
    result = {}
    for model, data in stats.items():
        if not data["ratings"]:
            continue

        ratings_list = data["ratings"]
        total_ratings = len(ratings_list)
        avg_rating = statistics.mean(ratings_list)
        win_rate = (data["rating_distribution"][5] / total_ratings) * 100

        # Calculate trend (compare first half vs second half)
        trend = "stable"
        if total_ratings >= 4:
            mid = total_ratings // 2
            first_half_avg = statistics.mean(ratings_list[:mid])
            second_half_avg = statistics.mean(ratings_list[mid:])
            diff = second_half_avg - first_half_avg
            if diff > 0.3:
                trend = "improving"
            elif diff < -0.3:
                trend = "declining"

        # Find best categories (categories with avg rating >= 4.0)
        best_categories = []
        for category, category_ratings in data["categories"].items():
            if category_ratings and statistics.mean(category_ratings) >= 4.0:
                best_categories.append(category)

        # Sort categories by average rating
        best_categories.sort(
            key=lambda c: statistics.mean(data["categories"][c]),
            reverse=True
        )

        # Analyze feedback sentiment (simple keyword-based)
        positive_keywords = ["good", "great", "excellent", "helpful", "clear", "accurate", "detailed"]
        negative_keywords = ["bad", "poor", "wrong", "confusing", "unclear", "incorrect", "missing"]

        positive_count = sum(
            1 for fb in data["feedback"]
            if any(kw in fb.lower() for kw in positive_keywords)
        )
        negative_count = sum(
            1 for fb in data["feedback"]
            if any(kw in fb.lower() for kw in negative_keywords)
        )

        result[model] = {
            "average_rating": round(avg_rating, 2),
            "total_ratings": total_ratings,
            "rating_distribution": data["rating_distribution"],
            "win_rate": round(win_rate, 1),
            "recent_trend": trend,
            "best_categories": best_categories[:3],  # Top 3 categories
            "feedback_summary": {
                "positive_count": positive_count,
                "negative_count": negative_count,
                "total_feedback": len(data["feedback"])
            }
        }

    return result


def get_recommendations_for_query(query: str, num_recommendations: int = 3) -> List[Dict]:
    """
    Get model recommendations based on query type and past ratings.

    Args:
        query: The user's query text
        num_recommendations: Number of recommendations to return

    Returns:
        List of recommended models with reasoning:
        [
            {
                "model_id": str,
                "confidence": float,  # 0-100
                "reason": str,
                "avg_rating": float,
                "category": str
            }
        ]
    """
    # Simple keyword-based categorization
    query_lower = query.lower()

    category = "general"
    keywords_map = {
        "code": ["code", "programming", "function", "bug", "debug", "implement", "script", "algorithm"],
        "creative": ["write", "story", "creative", "poem", "brainstorm", "idea", "imagine"],
        "research": ["research", "analyze", "study", "investigate", "explain", "understand", "learn"],
        "reasoning": ["solve", "calculate", "math", "logic", "prove", "why", "reason"]
    }

    for cat, keywords in keywords_map.items():
        if any(kw in query_lower for kw in keywords):
            category = cat
            break

    # Get model stats
    model_stats = get_model_rating_stats()

    if not model_stats:
        return []

    # Score models based on category performance and overall ratings
    recommendations = []
    for model, stats in model_stats.items():
        score = stats["average_rating"] * 20  # Convert 1-5 to 0-100 scale

        # Boost score if model excels in this category
        if category in stats["best_categories"]:
            category_position = stats["best_categories"].index(category)
            boost = 30 - (category_position * 10)  # First place: +30, second: +20, third: +10
            score += boost
            reason = f"Excellent at {category} tasks (avg {stats['average_rating']}/5)"
        else:
            reason = f"Good overall performance (avg {stats['average_rating']}/5)"

        # Boost for improving trend
        if stats["recent_trend"] == "improving":
            score += 10
            reason += " and improving"

        # Penalty for declining trend
        if stats["recent_trend"] == "declining":
            score -= 10

        # Ensure score is in valid range
        score = max(0, min(100, score))

        recommendations.append({
            "model_id": model,
            "confidence": round(score, 1),
            "reason": reason,
            "avg_rating": stats["average_rating"],
            "category": category
        })

    # Sort by confidence and return top N
    recommendations.sort(key=lambda x: x["confidence"], reverse=True)
    return recommendations[:num_recommendations]


def get_rating_analytics() -> Dict:
    """
    Get comprehensive rating analytics.

    Returns:
        {
            "total_ratings": int,
            "overall_avg_rating": float,
            "ratings_by_category": Dict[str, float],
            "most_rated_models": List[Dict],
            "highest_rated_models": List[Dict],
            "category_leaders": Dict[str, str]  # category -> best model
        }
    """
    data = _load_ratings()

    if not data["ratings"]:
        return {
            "total_ratings": 0,
            "overall_avg_rating": 0.0,
            "ratings_by_category": {},
            "most_rated_models": [],
            "highest_rated_models": [],
            "category_leaders": {}
        }

    all_ratings = [r["rating"] for r in data["ratings"]]

    # Ratings by category
    category_ratings = defaultdict(list)
    for rating in data["ratings"]:
        category_ratings[rating["query_category"]].append(rating["rating"])

    # Model rating counts
    model_counts = defaultdict(int)
    for rating in data["ratings"]:
        model_counts[rating["model_id"]] += 1

    # Get model stats for highest rated
    model_stats = get_model_rating_stats()

    # Most rated models
    most_rated = sorted(
        [{"model_id": m, "count": c} for m, c in model_counts.items()],
        key=lambda x: x["count"],
        reverse=True
    )[:5]

    # Highest rated models (with minimum 3 ratings)
    highest_rated = sorted(
        [
            {"model_id": m, "avg_rating": s["average_rating"], "total_ratings": s["total_ratings"]}
            for m, s in model_stats.items()
            if s["total_ratings"] >= 3
        ],
        key=lambda x: x["avg_rating"],
        reverse=True
    )[:5]

    # Category leaders
    category_leaders = {}
    for category in category_ratings.keys():
        category_model_ratings = defaultdict(list)
        for rating in data["ratings"]:
            if rating["query_category"] == category:
                category_model_ratings[rating["model_id"]].append(rating["rating"])

        # Find best model for this category (with min 2 ratings)
        best_model = None
        best_avg = 0
        for model, ratings in category_model_ratings.items():
            if len(ratings) >= 2:
                avg = statistics.mean(ratings)
                if avg > best_avg:
                    best_avg = avg
                    best_model = model

        if best_model:
            category_leaders[category] = best_model

    return {
        "total_ratings": len(all_ratings),
        "overall_avg_rating": round(statistics.mean(all_ratings), 2),
        "ratings_by_category": {
            cat: round(statistics.mean(ratings), 2)
            for cat, ratings in category_ratings.items()
        },
        "most_rated_models": most_rated,
        "highest_rated_models": highest_rated,
        "category_leaders": category_leaders
    }


def clear_ratings():
    """Clear all rating data."""
    _save_ratings({"ratings": []})
