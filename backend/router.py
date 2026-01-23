"""
RouteLLM - Intelligent Model Router for LLM Council.

Automatically selects the best model(s) based on query characteristics:
- Query type detection (code, creative, reasoning, research, general)
- Cost-performance optimization
- Model capability matching
"""

import re
from typing import List, Dict, Any, Tuple, Optional
from .config import AVAILABLE_MODELS


# ============ QUERY TYPE PATTERNS ============

QUERY_PATTERNS = {
    "code": [
        r"\b(code|coding|program|programming|function|class|method|debug|error|exception|fix|bug)\b",
        r"\b(python|javascript|typescript|java|c\+\+|rust|go|ruby|php|sql|html|css)\b",
        r"\b(api|endpoint|backend|frontend|database|query|algorithm|data structure)\b",
        r"\b(git|github|docker|kubernetes|aws|azure|deploy|devops)\b",
        r"```[\s\S]*```",  # Code blocks
        r"\b(implement|refactor|optimize|review|test|unittest)\b",
    ],
    "creative": [
        r"\b(write|create|compose|draft|story|poem|essay|article|blog)\b",
        r"\b(creative|imaginative|fiction|narrative|character|plot)\b",
        r"\b(brainstorm|ideate|generate ideas|concept|design)\b",
        r"\b(marketing|copy|slogan|tagline|advertisement)\b",
        r"\b(screenplay|script|dialogue|scene)\b",
    ],
    "reasoning": [
        r"\b(prove|theorem|mathematical|equation|calculate|compute)\b",
        r"\b(logic|logical|deduce|infer|conclude|therefore)\b",
        r"\b(step by step|chain of thought|reasoning|think through)\b",
        r"\b(puzzle|problem solving|brain teaser|riddle)\b",
        r"\b(analyze|evaluate|compare|contrast|assess)\b",
        r"\b(why|how come|what if|suppose|hypothesis)\b",
    ],
    "research": [
        r"\b(research|study|paper|journal|academic|scientific)\b",
        r"\b(source|citation|reference|evidence|data)\b",
        r"\b(current|latest|recent|news|update|today)\b",
        r"\b(search|find|look up|discover|explore)\b",
        r"\b(fact check|verify|confirm|accurate)\b",
    ],
    "vision": [
        r"\b(image|picture|photo|photograph|screenshot|diagram)\b",
        r"\b(see|look at|view|visual|display)\b",
        r"\b(analyze this image|describe this|what's in)\b",
        r"\b(ocr|text in image|extract from)\b",
    ],
    "long_context": [
        r"\b(document|file|pdf|book|chapter|article|report)\b",
        r"\b(summarize|summary|overview|key points)\b",
        r"\b(entire|whole|full|complete)\b",
        r"uploaded|attached|here is the",
    ],
}

# ============ MODEL CAPABILITIES ============

MODEL_CAPABILITIES = {
    # Top-tier models
    "anthropic/claude-opus-4": {
        "strengths": ["reasoning", "creative", "code", "research", "long_context"],
        "tier": 1,
        "cost": "high",
        "context_window": 200000,
    },
    "anthropic/claude-sonnet-4": {
        "strengths": ["code", "reasoning", "creative", "research"],
        "tier": 1,
        "cost": "medium",
        "context_window": 200000,
    },
    "openai/gpt-4.1": {
        "strengths": ["code", "reasoning", "creative", "research"],
        "tier": 1,
        "cost": "medium",
        "context_window": 128000,
    },
    "openai/gpt-4o": {
        "strengths": ["vision", "code", "creative", "reasoning"],
        "tier": 1,
        "cost": "medium",
        "context_window": 128000,
    },
    "google/gemini-2.5-pro": {
        "strengths": ["research", "reasoning", "code", "long_context"],
        "tier": 1,
        "cost": "medium",
        "context_window": 1000000,
    },

    # Reasoning specialists
    "openai/o3": {
        "strengths": ["reasoning", "code"],
        "tier": 1,
        "cost": "high",
        "context_window": 128000,
    },
    "openai/o4-mini": {
        "strengths": ["reasoning", "code"],
        "tier": 2,
        "cost": "low",
        "context_window": 128000,
    },
    "deepseek/deepseek-r1": {
        "strengths": ["reasoning", "code"],
        "tier": 1,
        "cost": "low",
        "context_window": 64000,
    },
    "qwen/qwq-32b-preview": {
        "strengths": ["reasoning"],
        "tier": 2,
        "cost": "low",
        "context_window": 32000,
    },

    # Code specialists
    "deepseek/deepseek-chat-v3": {
        "strengths": ["code", "reasoning"],
        "tier": 1,
        "cost": "low",
        "context_window": 64000,
    },
    "anthropic/claude-haiku-4": {
        "strengths": ["code", "creative"],
        "tier": 2,
        "cost": "low",
        "context_window": 200000,
    },

    # Research/Deep search specialists
    "perplexity/sonar-pro": {
        "strengths": ["research"],
        "tier": 1,
        "cost": "medium",
        "context_window": 200000,
    },
    "perplexity/sonar-deep-research": {
        "strengths": ["research"],
        "tier": 1,
        "cost": "high",
        "context_window": 200000,
    },

    # Long context specialists
    "google/gemini-2.5-flash": {
        "strengths": ["long_context", "research", "creative"],
        "tier": 2,
        "cost": "low",
        "context_window": 1000000,
    },
    "google/gemini-2.0-flash-thinking-exp:free": {
        "strengths": ["reasoning", "code"],
        "tier": 2,
        "cost": "free",
        "context_window": 32000,
    },

    # Vision specialists
    "openai/gpt-4o": {
        "strengths": ["vision", "code", "creative"],
        "tier": 1,
        "cost": "medium",
        "context_window": 128000,
    },
    "anthropic/claude-sonnet-4": {
        "strengths": ["vision", "code", "creative"],
        "tier": 1,
        "cost": "medium",
        "context_window": 200000,
    },

    # Free models
    "google/gemma-2-9b-it:free": {
        "strengths": ["creative"],
        "tier": 3,
        "cost": "free",
        "context_window": 8000,
    },
    "meta-llama/llama-3.3-70b-instruct:free": {
        "strengths": ["code", "creative"],
        "tier": 2,
        "cost": "free",
        "context_window": 128000,
    },
}


def detect_query_type(query: str) -> Dict[str, float]:
    """
    Detect the type of query based on keyword patterns.

    Returns:
        Dict with confidence scores for each query type (0.0 to 1.0)
    """
    query_lower = query.lower()
    scores = {}

    for query_type, patterns in QUERY_PATTERNS.items():
        matches = 0
        total_patterns = len(patterns)

        for pattern in patterns:
            if re.search(pattern, query_lower, re.IGNORECASE):
                matches += 1

        # Calculate confidence score
        scores[query_type] = min(1.0, matches / max(2, total_patterns * 0.5))

    # Normalize scores
    max_score = max(scores.values()) if scores else 0
    if max_score > 0:
        # Boost the top category
        for key in scores:
            if scores[key] == max_score:
                scores[key] = min(1.0, scores[key] * 1.2)

    # If no strong signals, default to general
    if max_score < 0.3:
        scores["general"] = 0.5

    return scores


def route_query(
    query: str,
    prefer_speed: bool = False,
    prefer_cost: bool = False,
    prefer_quality: bool = True,
    available_models: Optional[List[str]] = None,
    num_recommendations: int = 3,
) -> Dict[str, Any]:
    """
    Route a query to the best model(s) based on its characteristics.

    Args:
        query: The user's query
        prefer_speed: Prefer faster models
        prefer_cost: Prefer cheaper models
        prefer_quality: Prefer higher quality models
        available_models: List of available model IDs (defaults to all)
        num_recommendations: Number of models to recommend

    Returns:
        Dict with:
        - query_type: Detected query type with confidence
        - recommended_models: List of recommended model IDs
        - reasoning: Explanation of the routing decision
    """
    # Detect query type
    type_scores = detect_query_type(query)

    # Get primary query type
    primary_type = max(type_scores, key=type_scores.get)
    primary_confidence = type_scores[primary_type]

    # Get available models (intersection with configured models)
    if available_models is None:
        available_models = list(AVAILABLE_MODELS.keys())

    # Score each model for this query
    model_scores: List[Tuple[str, float, str]] = []

    for model_id in available_models:
        if model_id not in MODEL_CAPABILITIES:
            continue

        caps = MODEL_CAPABILITIES[model_id]
        score = 0.0
        reasons = []

        # Score based on capability match
        for query_type, confidence in type_scores.items():
            if confidence > 0.2 and query_type in caps["strengths"]:
                type_bonus = confidence * 2.0
                score += type_bonus
                if confidence > 0.5:
                    reasons.append(f"strong at {query_type}")

        # Tier bonus (1 = best)
        tier_bonus = (4 - caps["tier"]) * 0.5
        score += tier_bonus

        # Cost preference
        if prefer_cost:
            if caps["cost"] == "free":
                score += 1.5
                reasons.append("free")
            elif caps["cost"] == "low":
                score += 1.0
                reasons.append("low cost")
            elif caps["cost"] == "medium":
                score += 0.3

        # Quality preference
        if prefer_quality:
            if caps["tier"] == 1:
                score += 1.0
                reasons.append("top tier")

        # Speed preference (smaller models tend to be faster)
        if prefer_speed and caps["cost"] in ["free", "low"]:
            score += 0.5
            reasons.append("fast")

        # Check for long context needs
        query_length = len(query)
        if query_length > 5000 and caps["context_window"] >= 100000:
            score += 0.5
            reasons.append("long context")
        elif "long_context" in type_scores and type_scores["long_context"] > 0.3:
            if caps["context_window"] >= 500000:
                score += 1.0
                reasons.append("1M+ context")

        model_scores.append((model_id, score, ", ".join(reasons[:2])))

    # Sort by score and get top recommendations
    model_scores.sort(key=lambda x: x[1], reverse=True)

    recommendations = []
    for model_id, score, reason in model_scores[:num_recommendations]:
        model_info = AVAILABLE_MODELS.get(model_id, {})
        recommendations.append({
            "model_id": model_id,
            "name": model_info.get("name", model_id.split("/")[1]),
            "score": round(score, 2),
            "reason": reason,
            "cost": MODEL_CAPABILITIES.get(model_id, {}).get("cost", "unknown"),
        })

    # Build reasoning explanation
    reasoning_parts = [f"Query type: {primary_type} ({primary_confidence:.0%} confidence)"]

    if type_scores.get("code", 0) > 0.3:
        reasoning_parts.append("Detected coding-related content")
    if type_scores.get("reasoning", 0) > 0.3:
        reasoning_parts.append("Complex reasoning may be required")
    if type_scores.get("research", 0) > 0.3:
        reasoning_parts.append("Research/search capabilities helpful")
    if type_scores.get("creative", 0) > 0.3:
        reasoning_parts.append("Creative writing task detected")
    if type_scores.get("vision", 0) > 0.3:
        reasoning_parts.append("Vision/image analysis needed")
    if type_scores.get("long_context", 0) > 0.3:
        reasoning_parts.append("Long context window recommended")

    return {
        "query_type": primary_type,
        "type_scores": {k: round(v, 2) for k, v in type_scores.items() if v > 0.1},
        "primary_confidence": round(primary_confidence, 2),
        "recommended_models": recommendations,
        "reasoning": ". ".join(reasoning_parts),
        "preferences": {
            "speed": prefer_speed,
            "cost": prefer_cost,
            "quality": prefer_quality,
        }
    }


def get_quick_recommendation(query: str) -> str:
    """
    Get a single quick model recommendation for a query.

    Returns:
        The recommended model ID
    """
    result = route_query(query, num_recommendations=1)
    if result["recommended_models"]:
        return result["recommended_models"][0]["model_id"]
    return "anthropic/claude-sonnet-4"  # Default fallback


def get_council_for_query(query: str, max_models: int = 5) -> List[str]:
    """
    Get an optimal council composition for a query.

    Returns:
        List of model IDs optimized for the query type
    """
    result = route_query(query, num_recommendations=max_models * 2)

    # Get diverse models (different providers and strengths)
    council = []
    providers_used = set()

    for rec in result["recommended_models"]:
        model_id = rec["model_id"]
        provider = model_id.split("/")[0]

        # Limit models per provider for diversity
        if providers_used.count(provider) < 2:
            council.append(model_id)
            providers_used.add(provider)

        if len(council) >= max_models:
            break

    return council
