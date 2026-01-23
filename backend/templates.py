"""Prompt Templates Library for LLM Council."""

import json
import os
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from .config import DATA_DIR


TEMPLATES_FILE = os.path.join(DATA_DIR, "templates.json")


def ensure_templates_file():
    """Ensure the templates file exists with default templates."""
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)

    if not os.path.exists(TEMPLATES_FILE):
        # Create default templates
        default_templates = [
            {
                "id": str(uuid.uuid4()),
                "name": "Content Brief",
                "category": "content",
                "prompt_text": "Create a comprehensive content brief for {{topic}}. Target audience: {{audience}}. Key objectives: {{objectives}}",
                "variables": ["topic", "audience", "objectives"],
                "is_default": True,
                "created_at": datetime.utcnow().isoformat()
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Ad Copy Generator",
                "category": "marketing",
                "prompt_text": "Generate 5 compelling ad copy variations for {{product}} targeting {{audience}}. Focus on {{benefit}}. Include call-to-action.",
                "variables": ["product", "audience", "benefit"],
                "is_default": True,
                "created_at": datetime.utcnow().isoformat()
            },
            {
                "id": str(uuid.uuid4()),
                "name": "SEO Meta Description",
                "category": "seo",
                "prompt_text": "Write an SEO-optimized meta description (150-160 characters) for a page about {{topic}}. Include primary keyword: {{keyword}}",
                "variables": ["topic", "keyword"],
                "is_default": True,
                "created_at": datetime.utcnow().isoformat()
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Social Media Post",
                "category": "social",
                "prompt_text": "Create an engaging {{platform}} post about {{topic}}. Tone: {{tone}}. Include relevant hashtags and emoji.",
                "variables": ["platform", "topic", "tone"],
                "is_default": True,
                "created_at": datetime.utcnow().isoformat()
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Email Subject Lines",
                "category": "email",
                "prompt_text": "Generate 10 compelling email subject lines for {{campaign_type}} about {{topic}}. Target audience: {{audience}}. A/B test friendly.",
                "variables": ["campaign_type", "topic", "audience"],
                "is_default": True,
                "created_at": datetime.utcnow().isoformat()
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Competitor Analysis",
                "category": "research",
                "prompt_text": "Analyze {{competitor}} in the {{industry}} industry. Compare to {{our_company}} focusing on: {{focus_areas}}",
                "variables": ["competitor", "industry", "our_company", "focus_areas"],
                "is_default": True,
                "created_at": datetime.utcnow().isoformat()
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Blog Outline",
                "category": "content",
                "prompt_text": "Create a detailed blog post outline for '{{title}}'. Target word count: {{word_count}}. Target audience: {{audience}}. Include H2/H3 structure.",
                "variables": ["title", "word_count", "audience"],
                "is_default": True,
                "created_at": datetime.utcnow().isoformat()
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Product Description",
                "category": "ecommerce",
                "prompt_text": "Write a persuasive product description for {{product_name}}. Key features: {{features}}. Target customer: {{target_customer}}. Emphasize benefits over features.",
                "variables": ["product_name", "features", "target_customer"],
                "is_default": True,
                "created_at": datetime.utcnow().isoformat()
            }
        ]

        with open(TEMPLATES_FILE, 'w') as f:
            json.dump(default_templates, f, indent=2)


def load_templates() -> List[Dict[str, Any]]:
    """
    Load all templates from storage.

    Returns:
        List of template dicts
    """
    ensure_templates_file()

    with open(TEMPLATES_FILE, 'r') as f:
        return json.load(f)


def save_templates(templates: List[Dict[str, Any]]):
    """
    Save templates to storage.

    Args:
        templates: List of template dicts to save
    """
    ensure_templates_file()

    with open(TEMPLATES_FILE, 'w') as f:
        json.dump(templates, f, indent=2)


def list_templates(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List all templates, optionally filtered by category.

    Args:
        category: Optional category filter

    Returns:
        List of template dicts
    """
    templates = load_templates()

    if category:
        templates = [t for t in templates if t.get("category") == category]

    # Sort by default status (defaults first) then by creation date
    templates.sort(key=lambda x: (not x.get("is_default", False), x.get("created_at", "")))

    return templates


def get_template(template_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific template by ID.

    Args:
        template_id: Template identifier

    Returns:
        Template dict or None if not found
    """
    templates = load_templates()

    for template in templates:
        if template["id"] == template_id:
            return template

    return None


def create_template(
    name: str,
    category: str,
    prompt_text: str,
    variables: List[str]
) -> Dict[str, Any]:
    """
    Create a new custom template.

    Args:
        name: Template name
        category: Template category
        prompt_text: Prompt text with {{variable}} placeholders
        variables: List of variable names (without braces)

    Returns:
        Created template dict
    """
    templates = load_templates()

    new_template = {
        "id": str(uuid.uuid4()),
        "name": name,
        "category": category,
        "prompt_text": prompt_text,
        "variables": variables,
        "is_default": False,
        "created_at": datetime.utcnow().isoformat()
    }

    templates.append(new_template)
    save_templates(templates)

    return new_template


def update_template(
    template_id: str,
    name: Optional[str] = None,
    category: Optional[str] = None,
    prompt_text: Optional[str] = None,
    variables: Optional[List[str]] = None
) -> Optional[Dict[str, Any]]:
    """
    Update an existing template.

    Args:
        template_id: Template identifier
        name: Optional new name
        category: Optional new category
        prompt_text: Optional new prompt text
        variables: Optional new variables list

    Returns:
        Updated template dict or None if not found
    """
    templates = load_templates()

    for i, template in enumerate(templates):
        if template["id"] == template_id:
            # Don't allow updating default templates
            if template.get("is_default", False):
                return None

            if name is not None:
                template["name"] = name
            if category is not None:
                template["category"] = category
            if prompt_text is not None:
                template["prompt_text"] = prompt_text
            if variables is not None:
                template["variables"] = variables

            template["updated_at"] = datetime.utcnow().isoformat()

            templates[i] = template
            save_templates(templates)

            return template

    return None


def delete_template(template_id: str) -> bool:
    """
    Delete a template.

    Args:
        template_id: Template identifier

    Returns:
        True if deleted, False if not found or is default template
    """
    templates = load_templates()

    for i, template in enumerate(templates):
        if template["id"] == template_id:
            # Don't allow deleting default templates
            if template.get("is_default", False):
                return False

            templates.pop(i)
            save_templates(templates)
            return True

    return False


def get_categories() -> List[str]:
    """
    Get list of all unique template categories.

    Returns:
        Sorted list of category names
    """
    templates = load_templates()
    categories = set(t.get("category", "general") for t in templates)
    return sorted(categories)


def fill_template(template_id: str, variable_values: Dict[str, str]) -> Optional[str]:
    """
    Fill in a template with provided variable values.

    Args:
        template_id: Template identifier
        variable_values: Dict mapping variable names to values

    Returns:
        Filled prompt text or None if template not found
    """
    template = get_template(template_id)

    if not template:
        return None

    prompt_text = template["prompt_text"]

    # Replace all {{variable}} placeholders with values
    for var_name, var_value in variable_values.items():
        placeholder = f"{{{{{var_name}}}}}"
        prompt_text = prompt_text.replace(placeholder, var_value)

    return prompt_text
