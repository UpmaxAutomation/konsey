"""Predefined workflow templates for LLM Council canvas boards.

Each template defines a reusable multi-step pipeline that can be
instantiated on any board.  Templates are pure data -- no database
interaction happens here.
"""

from typing import Optional


# ──────────────────────────────────────────────
# Template definitions
# ──────────────────────────────────────────────

TEMPLATES: list[dict] = [
    # 1. Research Pipeline
    {
        "id": "research_pipeline",
        "name": "Research Pipeline",
        "description": "Structured research workflow: gather sources, analyze with multiple models, extract findings, and produce recommendations.",
        "icon": "search",
        "category": "research",
        "steps": [
            {
                "step_index": 0,
                "step_type": "ai_transform",
                "name": "Search & Gather",
                "prompt_template": (
                    "Analyze the following topic and identify key aspects to research:\n\n"
                    "{{input}}\n\n"
                    "Provide a structured breakdown of subtopics and key questions."
                ),
            },
            {
                "step_index": 1,
                "step_type": "council_query",
                "name": "Multi-model Analysis",
                "prompt_template": "{{input}}",
            },
            {
                "step_index": 2,
                "step_type": "ai_transform",
                "name": "Key Findings",
                "prompt_template": (
                    "Based on the following research analysis, extract and summarize "
                    "the most important findings:\n\n"
                    "{{input}}\n\n"
                    "Provide numbered key findings with supporting evidence."
                ),
            },
            {
                "step_index": 3,
                "step_type": "ai_transform",
                "name": "Recommendations",
                "prompt_template": (
                    "Based on these key findings, provide actionable recommendations:\n\n"
                    "{{input}}\n\n"
                    "Format as prioritized recommendations with rationale."
                ),
            },
        ],
    },

    # 2. Decision Matrix
    {
        "id": "decision_matrix",
        "name": "Decision Matrix",
        "description": "Systematic decision-making: define options, score against criteria with multi-model input, review, and finalize.",
        "icon": "grid",
        "category": "decision",
        "steps": [
            {
                "step_index": 0,
                "step_type": "ai_transform",
                "name": "Define Options",
                "prompt_template": (
                    "Given the following decision context, identify and describe all "
                    "viable options:\n\n"
                    "{{input}}\n\n"
                    "List each option with pros and cons."
                ),
            },
            {
                "step_index": 1,
                "step_type": "ai_transform",
                "name": "Evaluation Criteria",
                "prompt_template": (
                    "For these options, define evaluation criteria and score each option:\n\n"
                    "{{input}}\n\n"
                    "Use a 1-10 scale for each criterion."
                ),
            },
            {
                "step_index": 2,
                "step_type": "council_query",
                "name": "Multi-perspective Scoring",
                "prompt_template": "{{input}}",
            },
            {
                "step_index": 3,
                "step_type": "human_review",
                "name": "Review Scores",
                "prompt_template": "",
            },
            {
                "step_index": 4,
                "step_type": "ai_transform",
                "name": "Final Decision",
                "prompt_template": (
                    "Based on the reviewed scores and analysis, provide a final decision "
                    "recommendation:\n\n"
                    "{{input}}\n\n"
                    "Include confidence level and risk assessment."
                ),
            },
        ],
    },

    # 3. Content Pipeline
    {
        "id": "content_pipeline",
        "name": "Content Pipeline",
        "description": "End-to-end content creation: outline, draft, multi-model peer review, and polished final version.",
        "icon": "file-text",
        "category": "content",
        "steps": [
            {
                "step_index": 0,
                "step_type": "ai_transform",
                "name": "Outline",
                "prompt_template": (
                    "Create a detailed outline for the following content:\n\n"
                    "{{input}}\n\n"
                    "Include main sections, subsections, and key points for each."
                ),
            },
            {
                "step_index": 1,
                "step_type": "ai_transform",
                "name": "Draft",
                "prompt_template": (
                    "Write a complete draft based on this outline:\n\n"
                    "{{input}}\n\n"
                    "Maintain a professional, engaging tone."
                ),
            },
            {
                "step_index": 2,
                "step_type": "council_query",
                "name": "Peer Review",
                "prompt_template": "{{input}}",
            },
            {
                "step_index": 3,
                "step_type": "ai_transform",
                "name": "Final Version",
                "prompt_template": (
                    "Incorporate the review feedback and produce the final polished version:\n\n"
                    "{{input}}"
                ),
            },
        ],
    },

    # 4. SWOT Analysis
    {
        "id": "swot_analysis",
        "name": "SWOT Analysis",
        "description": "Comprehensive SWOT: internal strengths/weaknesses, external opportunities/threats, combined matrix, and strategic recommendations.",
        "icon": "layout",
        "category": "strategy",
        "steps": [
            {
                "step_index": 0,
                "step_type": "ai_transform",
                "name": "Strengths & Weaknesses",
                "prompt_template": (
                    "Analyze the following for internal strengths and weaknesses:\n\n"
                    "{{input}}\n\n"
                    "Provide detailed S and W analysis."
                ),
            },
            {
                "step_index": 1,
                "step_type": "ai_transform",
                "name": "Opportunities & Threats",
                "prompt_template": (
                    "Analyze the following for external opportunities and threats:\n\n"
                    "{{input}}\n\n"
                    "Provide detailed O and T analysis."
                ),
            },
            {
                "step_index": 2,
                "step_type": "combine",
                "name": "SWOT Matrix",
                "prompt_template": "Combine into a complete SWOT matrix with cross-analysis",
            },
            {
                "step_index": 3,
                "step_type": "ai_transform",
                "name": "Strategy",
                "prompt_template": (
                    "Based on this SWOT analysis, develop strategic recommendations:\n\n"
                    "{{input}}\n\n"
                    "Suggest strategies that leverage strengths against opportunities "
                    "and mitigate weaknesses against threats."
                ),
            },
        ],
    },

    # 5. Brainstorm to Action
    {
        "id": "brainstorm_to_action",
        "name": "Brainstorm to Action",
        "description": "From ideas to execution: multi-model brainstorm, cluster into themes, prioritize by impact, and generate action items.",
        "icon": "zap",
        "category": "ideation",
        "steps": [
            {
                "step_index": 0,
                "step_type": "council_query",
                "name": "Brainstorm",
                "prompt_template": "{{input}}",
            },
            {
                "step_index": 1,
                "step_type": "ai_transform",
                "name": "Cluster & Theme",
                "prompt_template": (
                    "Organize and cluster these brainstormed ideas into themes:\n\n"
                    "{{input}}\n\n"
                    "Group related ideas and identify common patterns."
                ),
            },
            {
                "step_index": 2,
                "step_type": "ai_transform",
                "name": "Prioritize",
                "prompt_template": (
                    "Prioritize these clustered ideas using impact vs effort analysis:\n\n"
                    "{{input}}\n\n"
                    "Rank by quick wins, strategic initiatives, and nice-to-haves."
                ),
            },
            {
                "step_index": 3,
                "step_type": "ai_transform",
                "name": "Action Items",
                "prompt_template": (
                    "Convert the prioritized ideas into specific, actionable items:\n\n"
                    "{{input}}\n\n"
                    "Each action item should have: description, owner placeholder, "
                    "timeline, success metric."
                ),
            },
        ],
    },
]


# ──────────────────────────────────────────────
# Public helpers
# ──────────────────────────────────────────────

def list_templates() -> list[dict]:
    """Return all available workflow templates."""
    return TEMPLATES


def get_template(template_id: str) -> Optional[dict]:
    """Return a single template by its id, or None if not found."""
    return next((t for t in TEMPLATES if t["id"] == template_id), None)
