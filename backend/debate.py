"""Debate mode for LLM Council - pro vs con arguments."""

from typing import List, Dict, Any, Tuple
from .openrouter import query_models_parallel
from .config import get_council_models, get_chairman_model


async def run_debate(topic: str, rounds: int = 2) -> Dict[str, Any]:
    """
    Run a structured debate between council models.

    Half of the models argue FOR the topic, half argue AGAINST.
    Each round consists of pro arguments followed by con rebuttals.
    Chairman synthesizes both sides at the end.

    Args:
        topic: The debate topic/question
        rounds: Number of debate rounds (default: 2)

    Returns:
        Dict with structure:
        {
            "topic": str,
            "rounds": [
                {
                    "round_number": int,
                    "pro": [{"model": str, "argument": str}, ...],
                    "con": [{"model": str, "argument": str}, ...]
                },
                ...
            ],
            "synthesis": {
                "model": str,
                "response": str
            }
        }
    """
    council_models = get_council_models()

    # Split models into pro and con teams
    midpoint = len(council_models) // 2
    pro_models = council_models[:midpoint]
    con_models = council_models[midpoint:]

    # Ensure we have at least one model on each side
    if not pro_models or not con_models:
        return {
            "topic": topic,
            "rounds": [],
            "synthesis": {
                "model": "error",
                "response": "Need at least 2 models to run a debate (one pro, one con)"
            }
        }

    debate_rounds = []

    # Keep track of all arguments for context
    all_pro_arguments = []
    all_con_arguments = []

    for round_num in range(1, rounds + 1):
        # Build context from previous rounds
        context = ""
        if round_num > 1:
            context = "\n\n**Previous Arguments:**\n"
            for prev_round in debate_rounds:
                context += f"\n**Round {prev_round['round_number']}:**\n"
                context += "PRO side:\n"
                for arg in prev_round['pro']:
                    context += f"- {arg['argument'][:200]}...\n"
                context += "\nCON side:\n"
                for arg in prev_round['con']:
                    context += f"- {arg['argument'][:200]}...\n"

        # Pro side argues first
        pro_prompt = f"""You are arguing FOR the following position in a structured debate:

**Topic:** {topic}

**Your Position:** You support this position and will argue in favor of it.

**Round {round_num} of {rounds}**
{context}

Your task: Provide a clear, well-reasoned argument supporting this position. Consider:
- Key benefits and advantages
- Evidence and examples supporting your view
- Counterarguments to potential objections
{"- Responses to the CON side's previous arguments" if round_num > 1 else ""}

Provide your argument (2-3 paragraphs):"""

        # Con side argues second (with pro arguments as context)
        con_prompt = f"""You are arguing AGAINST the following position in a structured debate:

**Topic:** {topic}

**Your Position:** You oppose this position and will argue against it.

**Round {round_num} of {rounds}**
{context}

Your task: Provide a clear, well-reasoned argument opposing this position. Consider:
- Key concerns and disadvantages
- Evidence and examples supporting your view
- Counterarguments to the PRO side's claims
{"- Rebuttals to the PRO side's arguments in this round" if round_num > 1 else ""}

Provide your argument (2-3 paragraphs):"""

        # Get pro arguments
        pro_messages = [{"role": "user", "content": pro_prompt}]
        pro_responses = await query_models_parallel(pro_models, pro_messages)

        pro_arguments = []
        for model, response in pro_responses.items():
            if response is not None:
                argument = response.get('content', '')
                pro_arguments.append({
                    "model": model,
                    "argument": argument
                })
                all_pro_arguments.append(f"{model}: {argument}")

        # Add pro arguments to con prompt for rebuttal
        if pro_arguments:
            pro_summary = "\n\n**PRO side arguments in this round:**\n"
            for arg in pro_arguments:
                pro_summary += f"\n- {arg['argument']}\n"
            con_prompt += pro_summary

        # Get con arguments (with pro arguments as context)
        con_messages = [{"role": "user", "content": con_prompt}]
        con_responses = await query_models_parallel(con_models, con_messages)

        con_arguments = []
        for model, response in con_responses.items():
            if response is not None:
                argument = response.get('content', '')
                con_arguments.append({
                    "model": model,
                    "argument": argument
                })
                all_con_arguments.append(f"{model}: {argument}")

        # Store round results
        debate_rounds.append({
            "round_number": round_num,
            "pro": pro_arguments,
            "con": con_arguments
        })

    # Chairman synthesis
    synthesis = await synthesize_debate(
        topic=topic,
        rounds=debate_rounds,
        pro_models=pro_models,
        con_models=con_models
    )

    return {
        "topic": topic,
        "rounds": debate_rounds,
        "synthesis": synthesis,
        "metadata": {
            "total_rounds": rounds,
            "pro_models": pro_models,
            "con_models": con_models
        }
    }


async def synthesize_debate(
    topic: str,
    rounds: List[Dict[str, Any]],
    pro_models: List[str],
    con_models: List[str]
) -> Dict[str, Any]:
    """
    Chairman synthesizes the debate by weighing both sides.

    Args:
        topic: The debate topic
        rounds: List of debate rounds with pro/con arguments
        pro_models: List of models arguing pro
        con_models: List of models arguing con

    Returns:
        Dict with 'model' and 'response' keys
    """
    # Build comprehensive debate summary
    debate_summary = f"**Debate Topic:** {topic}\n\n"
    debate_summary += f"**PRO Team:** {', '.join(pro_models)}\n"
    debate_summary += f"**CON Team:** {', '.join(con_models)}\n\n"

    for round_data in rounds:
        round_num = round_data['round_number']
        debate_summary += f"## Round {round_num}\n\n"

        debate_summary += "### PRO Arguments:\n"
        for arg in round_data['pro']:
            debate_summary += f"\n**{arg['model']}:**\n{arg['argument']}\n"

        debate_summary += "\n### CON Arguments:\n"
        for arg in round_data['con']:
            debate_summary += f"\n**{arg['model']}:**\n{arg['argument']}\n"

        debate_summary += "\n---\n\n"

    chairman_prompt = f"""You are the Chairman moderating a structured debate. Multiple AI models have debated a topic, with half arguing FOR and half arguing AGAINST.

{debate_summary}

Your task as Chairman is to:
1. Summarize the key arguments from both sides
2. Evaluate the strength of each side's reasoning and evidence
3. Identify areas of agreement and disagreement
4. Provide a balanced, nuanced final perspective that weighs both positions

Consider:
- Which side presented stronger evidence?
- Which arguments were most compelling?
- What are the legitimate concerns on both sides?
- Is there a middle ground or synthesis position?

Provide your final synthesis (3-4 paragraphs):"""

    chairman_model = get_chairman_model()
    from .openrouter import query_model

    messages = [{"role": "user", "content": chairman_prompt}]
    response = await query_model(chairman_model, messages)

    if response is None:
        return {
            "model": chairman_model,
            "response": "Error: Unable to generate debate synthesis."
        }

    return {
        "model": chairman_model,
        "response": response.get('content', '')
    }
