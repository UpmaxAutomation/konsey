"""Configuration for the LLM Council."""

import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root (parent of backend directory)
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)
# Also try loading from current directory (for direct execution)
load_dotenv()

# OpenRouter API key from environment (can be overridden via Settings)
_OPENROUTER_API_KEY_ENV = os.getenv("OPENROUTER_API_KEY", "")
# Perplexity API key from environment (can be overridden via Settings)
_PERPLEXITY_API_KEY_ENV = os.getenv("PERPLEXITY_API_KEY", "")

# Storage backend: "json" (file-based) or "database" (PostgreSQL)
# Set USE_DATABASE=true to use PostgreSQL instead of JSON files
USE_DATABASE = os.getenv("USE_DATABASE", "false").lower() == "true"

# Default anonymous user ID for database storage when auth is not used
ANONYMOUS_USER_ID = "00000000-0000-0000-0000-000000000000"

# Default council members - list of OpenRouter model identifiers
DEFAULT_COUNCIL_MODELS = [
    "openai/gpt-4o",
    "google/gemini-2.5-flash",
    "anthropic/claude-sonnet-4",
    "x-ai/grok-3",
]

# Default chairman model - synthesizes final response
DEFAULT_CHAIRMAN_MODEL = "google/gemini-2.5-flash"

# Council Presets - Specialized configurations for different use cases
COUNCIL_PRESETS = {
    "code_review": {
        "name": "Code Review Council",
        "description": "Expert code reviewers for analyzing code quality, bugs, and best practices",
        "models": ["anthropic/claude-sonnet-4", "openai/gpt-5.1-codex", "deepseek/deepseek-chat-v3", "qwen/qwen-2.5-coder-32b-instruct"],
        "chairman": "anthropic/claude-opus-4"
    },
    "research": {
        "name": "Research Council",
        "description": "Deep research and analysis with comprehensive information synthesis",
        "models": ["google/gemini-2.5-pro", "anthropic/claude-opus-4.5", "openai/gpt-5", "x-ai/grok-3"],
        "chairman": "google/gemini-2.5-pro"
    },
    "creative": {
        "name": "Creative Council",
        "description": "Creative writing, brainstorming, and innovative content generation",
        "models": ["anthropic/claude-sonnet-4", "openai/gpt-5", "google/gemini-2.5-flash"],
        "chairman": "anthropic/claude-sonnet-4"
    },
    "reasoning": {
        "name": "Reasoning Council",
        "description": "Complex logic, mathematics, and analytical problem solving",
        "models": ["openai/o3", "deepseek/deepseek-r1", "qwen/qwq-32b", "openai/o4-mini"],
        "chairman": "openai/o3"
    },
    "budget": {
        "name": "Budget Council",
        "description": "Cost-effective models maintaining good quality at minimal expense",
        "models": ["deepseek/deepseek-r1-0528", "qwen/qwen-2.5-coder-32b-instruct", "google/gemma-2-9b-it:free"],
        "chairman": "google/gemini-2.5-flash"
    }
}

# Available models for selection (with pricing per 1M tokens)
AVAILABLE_MODELS = {
    # ============ OpenAI ============
    "openai/gpt-5.2-pro": {"name": "GPT-5.2 Pro", "input_cost": 10.00, "output_cost": 30.00},
    "openai/gpt-5.2": {"name": "GPT-5.2", "input_cost": 6.00, "output_cost": 18.00},
    "openai/gpt-5.2-chat": {"name": "GPT-5.2 Chat", "input_cost": 3.00, "output_cost": 12.00},
    "openai/gpt-5.1": {"name": "GPT-5.1", "input_cost": 5.00, "output_cost": 15.00},
    "openai/gpt-5.1-chat": {"name": "GPT-5.1 Chat", "input_cost": 2.50, "output_cost": 10.00},
    "openai/gpt-5.1-codex": {"name": "GPT-5.1 Codex", "input_cost": 5.00, "output_cost": 15.00},
    "openai/gpt-5.1-codex-mini": {"name": "GPT-5.1 Codex Mini", "input_cost": 2.00, "output_cost": 8.00},
    "openai/gpt-5.1-codex-max": {"name": "GPT-5.1 Codex Max", "input_cost": 8.00, "output_cost": 24.00},
    "openai/gpt-5": {"name": "GPT-5", "input_cost": 5.00, "output_cost": 15.00},
    "openai/gpt-5-image": {"name": "GPT-5 Image", "input_cost": 5.00, "output_cost": 15.00},
    "openai/gpt-4.5-preview": {"name": "GPT-4.5 Preview", "input_cost": 75.00, "output_cost": 150.00},
    "openai/gpt-4o": {"name": "GPT-4o", "input_cost": 2.50, "output_cost": 10.00},
    "openai/gpt-4o-mini": {"name": "GPT-4o Mini", "input_cost": 0.15, "output_cost": 0.60},
    "openai/o3-deep-research": {"name": "O3 Deep Research", "input_cost": 20.00, "output_cost": 80.00},
    "openai/o3": {"name": "O3", "input_cost": 2.00, "output_cost": 8.00},
    "openai/o3-pro": {"name": "O3 Pro", "input_cost": 20.00, "output_cost": 80.00},
    "openai/o4-mini": {"name": "O4 Mini", "input_cost": 1.10, "output_cost": 4.40},
    "openai/o4-mini-deep-research": {"name": "O4 Mini Deep Research", "input_cost": 2.00, "output_cost": 8.00},
    "openai/o1": {"name": "O1", "input_cost": 15.00, "output_cost": 60.00},
    "openai/o1-mini": {"name": "O1 Mini", "input_cost": 3.00, "output_cost": 12.00},
    "openai/o1-pro": {"name": "O1 Pro", "input_cost": 150.00, "output_cost": 600.00},

    # ============ Anthropic ============
    "anthropic/claude-opus-4.5": {"name": "Claude Opus 4.5", "input_cost": 5.00, "output_cost": 25.00},
    "anthropic/claude-opus-4": {"name": "Claude Opus 4", "input_cost": 15.00, "output_cost": 75.00},
    "anthropic/claude-sonnet-4": {"name": "Claude Sonnet 4", "input_cost": 3.00, "output_cost": 15.00},
    "anthropic/claude-haiku-4.5": {"name": "Claude Haiku 4.5", "input_cost": 1.00, "output_cost": 5.00},
    "anthropic/claude-3.5-haiku": {"name": "Claude 3.5 Haiku", "input_cost": 0.80, "output_cost": 4.00},
    "anthropic/claude-3-haiku": {"name": "Claude 3 Haiku", "input_cost": 0.25, "output_cost": 1.25},

    # ============ Google ============
    "google/gemini-3-flash-preview": {"name": "Gemini 3 Flash Preview", "input_cost": 0.15, "output_cost": 0.60},
    "google/gemini-3-pro-preview": {"name": "Gemini 3 Pro Preview", "input_cost": 1.25, "output_cost": 10.00},
    "google/gemini-2.5-pro": {"name": "Gemini 2.5 Pro", "input_cost": 1.25, "output_cost": 10.00},
    "google/gemini-2.5-flash": {"name": "Gemini 2.5 Flash", "input_cost": 0.15, "output_cost": 0.60},
    "google/gemini-2.5-flash-preview-05-20": {"name": "Gemini 2.5 Flash Preview", "input_cost": 0.15, "output_cost": 0.60},
    "google/gemini-2.0-flash": {"name": "Gemini 2.0 Flash", "input_cost": 0.10, "output_cost": 0.40},
    "google/gemini-2.0-flash-lite": {"name": "Gemini 2.0 Flash Lite", "input_cost": 0.075, "output_cost": 0.30},

    # ============ xAI ============
    "x-ai/grok-4.1": {"name": "Grok 4.1", "input_cost": 3.00, "output_cost": 15.00},
    "x-ai/grok-4.1-fast": {"name": "Grok 4.1 Fast (2M context)", "input_cost": 5.00, "output_cost": 25.00},
    "x-ai/grok-4.1-thinking": {"name": "Grok 4.1 Thinking", "input_cost": 5.00, "output_cost": 25.00},
    "x-ai/grok-4-fast": {"name": "Grok 4 Fast (2M context)", "input_cost": 5.00, "output_cost": 25.00},
    "x-ai/grok-code-fast-1": {"name": "Grok Code Fast 1", "input_cost": 3.00, "output_cost": 15.00},
    "x-ai/grok-3": {"name": "Grok 3", "input_cost": 3.00, "output_cost": 15.00},
    "x-ai/grok-3-mini": {"name": "Grok 3 Mini", "input_cost": 0.30, "output_cost": 0.50},
    "x-ai/grok-3-fast": {"name": "Grok 3 Fast", "input_cost": 5.00, "output_cost": 25.00},

    # ============ Z.AI (Zhipu) ============
    "z-ai/glm-4.7": {"name": "GLM 4.7 (203K)", "input_cost": 0.40, "output_cost": 1.50},
    "z-ai/glm-4.6v": {"name": "GLM 4.6V Vision", "input_cost": 0.30, "output_cost": 0.90},
    "z-ai/glm-4-long": {"name": "GLM 4 Long (1M)", "input_cost": 0.20, "output_cost": 0.80},

    # ============ Meta Llama ============
    "meta-llama/llama-4-scout": {"name": "Llama 4 Scout", "input_cost": 0.25, "output_cost": 0.70},
    "meta-llama/llama-4-maverick": {"name": "Llama 4 Maverick", "input_cost": 0.25, "output_cost": 0.70},
    "meta-llama/llama-3.3-70b-instruct": {"name": "Llama 3.3 70B", "input_cost": 0.10, "output_cost": 0.10},
    "meta-llama/llama-3.1-405b-instruct": {"name": "Llama 3.1 405B", "input_cost": 0.80, "output_cost": 0.80},

    # ============ DeepSeek ============
    "deepseek/deepseek-chat-v3-0324": {"name": "DeepSeek V3 0324", "input_cost": 0.14, "output_cost": 0.28},
    "deepseek/deepseek-v3.2": {"name": "DeepSeek V3.2", "input_cost": 0.25, "output_cost": 0.38},
    "deepseek/deepseek-v3.2-speciale": {"name": "DeepSeek V3.2 Speciale", "input_cost": 0.27, "output_cost": 0.41},
    "deepseek/deepseek-r1": {"name": "DeepSeek R1", "input_cost": 0.55, "output_cost": 2.19},
    "deepseek/deepseek-r1-0528": {"name": "DeepSeek R1 0528", "input_cost": 0.55, "output_cost": 2.19},

    # ============ Mistral ============
    "mistralai/mistral-large-2512": {"name": "Mistral Large 3", "input_cost": 0.50, "output_cost": 1.50},
    "mistralai/mistral-large-2411": {"name": "Mistral Large 2", "input_cost": 2.00, "output_cost": 6.00},
    "mistralai/mistral-small-2503": {"name": "Mistral Small", "input_cost": 0.10, "output_cost": 0.30},
    "mistralai/devstral-2512": {"name": "Devstral 2", "input_cost": 0.05, "output_cost": 0.22},
    "mistralai/ministral-14b-2512": {"name": "Ministral 3 14B", "input_cost": 0.20, "output_cost": 0.20},
    "mistralai/codestral-latest": {"name": "Codestral", "input_cost": 0.30, "output_cost": 0.90},

    # ============ Qwen ============
    "qwen/qwen3-235b-a22b": {"name": "Qwen 3 235B", "input_cost": 0.50, "output_cost": 2.00},
    "qwen/qwen3-235b-a22b-thinking": {"name": "Qwen 3 235B Thinking", "input_cost": 0.80, "output_cost": 3.20},
    "qwen/qwen3-32b": {"name": "Qwen 3 32B", "input_cost": 0.10, "output_cost": 0.30},
    "qwen/qwen3-vl-32b-instruct": {"name": "Qwen 3 VL 32B", "input_cost": 0.50, "output_cost": 1.50},
    "qwen/qwen3-vl-8b-instruct": {"name": "Qwen 3 VL 8B", "input_cost": 0.08, "output_cost": 0.50},
    "qwen/qwen-2.5-72b-instruct": {"name": "Qwen 2.5 72B", "input_cost": 0.35, "output_cost": 0.40},
    "qwen/qwen-2.5-coder-32b-instruct": {"name": "Qwen 2.5 Coder 32B", "input_cost": 0.20, "output_cost": 0.20},
    "qwen/qwq-32b": {"name": "QwQ 32B", "input_cost": 0.20, "output_cost": 0.20},
    "qwen/qwq-32b-preview": {"name": "QwQ 32B Preview", "input_cost": 0.15, "output_cost": 0.15},

    # ============ Cohere ============
    "cohere/command-a": {"name": "Command A (256K)", "input_cost": 2.50, "output_cost": 10.00},
    "cohere/command-r-plus": {"name": "Command R+", "input_cost": 2.50, "output_cost": 10.00},
    "cohere/command-r": {"name": "Command R", "input_cost": 0.15, "output_cost": 0.60},

    # ============ Perplexity (Deep Search) ============
    "perplexity/sonar-pro": {"name": "Sonar Pro (Search)", "input_cost": 3.00, "output_cost": 15.00},
    "perplexity/sonar": {"name": "Sonar (Search)", "input_cost": 1.00, "output_cost": 5.00},
    "perplexity/sonar-deep-research": {"name": "Sonar Deep Research", "input_cost": 5.00, "output_cost": 20.00},
    "perplexity/sonar-reasoning-pro": {"name": "Sonar Reasoning Pro", "input_cost": 3.00, "output_cost": 15.00},

    # ============ Moonshot AI (Kimi) ============
    "moonshot/kimi-k2": {"name": "Kimi K2", "input_cost": 0.60, "output_cost": 2.40},
    "moonshot/kimi-k2-thinking": {"name": "Kimi K2 Thinking", "input_cost": 1.00, "output_cost": 4.00},

    # ============ MiniMax ============
    "minimax/m2": {"name": "MiniMax M2", "input_cost": 0.50, "output_cost": 2.00},
    "minimax/m2-reasoning": {"name": "MiniMax M2 Reasoning", "input_cost": 0.80, "output_cost": 3.20},

    # ============ Xiaomi ============
    "xiaomi/mimo-v2-flash": {"name": "MiMo V2 Flash", "input_cost": 0.10, "output_cost": 0.40},
    "xiaomi/mimo-v2-flash:free": {"name": "MiMo V2 Flash (Free)", "input_cost": 0.00, "output_cost": 0.00},

    # ============ 01.AI (Yi) ============
    "01-ai/yi-lightning": {"name": "Yi Lightning", "input_cost": 0.20, "output_cost": 0.20},
    "01-ai/yi-large": {"name": "Yi Large", "input_cost": 0.80, "output_cost": 0.80},

    # ============ Nous Research ============
    "nousresearch/hermes-3-llama-3.1-405b": {"name": "Hermes 3 405B", "input_cost": 0.80, "output_cost": 0.80},

    # ============ Free/Cheap Options ============
    "google/gemma-2-9b-it:free": {"name": "Gemma 2 9B (Free)", "input_cost": 0.00, "output_cost": 0.00},
    "google/gemma-3-27b-it:free": {"name": "Gemma 3 27B (Free)", "input_cost": 0.00, "output_cost": 0.00},
    "meta-llama/llama-3.2-3b-instruct:free": {"name": "Llama 3.2 3B (Free)", "input_cost": 0.00, "output_cost": 0.00},
    "meta-llama/llama-4-scout:free": {"name": "Llama 4 Scout (Free)", "input_cost": 0.00, "output_cost": 0.00},
    "mistralai/mistral-7b-instruct:free": {"name": "Mistral 7B (Free)", "input_cost": 0.00, "output_cost": 0.00},
    "deepseek/deepseek-r1:free": {"name": "DeepSeek R1 (Free)", "input_cost": 0.00, "output_cost": 0.00},
    "deepseek/deepseek-chat:free": {"name": "DeepSeek Chat (Free)", "input_cost": 0.00, "output_cost": 0.00},
    "qwen/qwen-2.5-72b-instruct:free": {"name": "Qwen 2.5 72B (Free)", "input_cost": 0.00, "output_cost": 0.00},
    "qwen/qwen3-32b:free": {"name": "Qwen 3 32B (Free)", "input_cost": 0.00, "output_cost": 0.00},
}

# Default personas for council models
DEFAULT_PERSONAS = {
    "default": "",
    "senior_engineer": "You are a senior software engineer with 15+ years of experience. Focus on code quality, best practices, and maintainability.",
    "security_expert": "You are a cybersecurity expert. Analyze for vulnerabilities, security risks, and suggest mitigations.",
    "product_manager": "You are a product manager. Consider user experience, business value, and feasibility.",
    "devil_advocate": "Challenge assumptions and point out potential flaws or overlooked issues.",
    "optimist": "Focus on possibilities and positive outcomes while being realistic.",
    "minimalist": "Prefer simple, elegant solutions. Less is more."
}

# Provider API endpoints for direct connections
PROVIDER_API_ENDPOINTS = {
    "openai": "https://api.openai.com/v1/chat/completions",
    "anthropic": "https://api.anthropic.com/v1/messages",
    "google": "https://generativelanguage.googleapis.com/v1beta/models",
    "x-ai": "https://api.x.ai/v1/chat/completions",
    "deepseek": "https://api.deepseek.com/v1/chat/completions",
    "mistralai": "https://api.mistral.ai/v1/chat/completions",
    "cohere": "https://api.cohere.ai/v1/chat",
    "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
    "perplexity": "https://api.perplexity.ai/chat/completions",
}

# Runtime configuration (can be changed via API)
_runtime_config = {
    "council_models": DEFAULT_COUNCIL_MODELS.copy(),
    "chairman_model": DEFAULT_CHAIRMAN_MODEL,
    "enhanced_features": {
        "web_search": True,
        "deep_search": False,
        "code_execution": True,
        "memory": True
    },
    "personas": {},  # model_id -> persona_key or custom text
    "custom_personas": {},  # persona_id -> custom persona text
    "api_keys": {
        "openrouter": "",
        "openai": "",
        "anthropic": "",
        "google": "",
        "x-ai": "",
        "deepseek": "",
        "mistralai": "",
        "cohere": "",
        "qwen": "",
        "perplexity": ""
    }
}

# Settings file path
SETTINGS_FILE = "data/settings.json"

def load_settings():
    """Load settings from file."""
    global _runtime_config
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r') as f:
                saved = json.load(f)
                _runtime_config["council_models"] = saved.get("council_models", DEFAULT_COUNCIL_MODELS.copy())
                _runtime_config["chairman_model"] = saved.get("chairman_model", DEFAULT_CHAIRMAN_MODEL)
                saved_features = saved.get("enhanced_features", {})
                _runtime_config["enhanced_features"] = {
                    "web_search": saved_features.get("web_search", True),
                    "deep_search": saved_features.get("deep_search", False),
                    "code_execution": saved_features.get("code_execution", True),
                    "memory": saved_features.get("memory", True)
                }
                _runtime_config["personas"] = saved.get("personas", {})
                _runtime_config["custom_personas"] = saved.get("custom_personas", {})
                _runtime_config["api_keys"] = saved.get("api_keys", {
                    "openai": "",
                    "anthropic": "",
                    "google": "",
                    "x-ai": "",
                    "deepseek": "",
                    "mistralai": "",
                    "cohere": "",
                    "qwen": "",
                    "perplexity": ""
                })
    except Exception as e:
        print(f"Error loading settings: {e}")

def save_settings():
    """Save settings to file."""
    try:
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(_runtime_config, f, indent=2)
    except Exception as e:
        print(f"Error saving settings: {e}")

def get_council_models():
    """Get current council models."""
    return _runtime_config["council_models"]

def set_council_models(models: list):
    """Set council models."""
    _runtime_config["council_models"] = models
    save_settings()

def get_chairman_model():
    """Get current chairman model."""
    return _runtime_config["chairman_model"]

def set_chairman_model(model: str):
    """Set chairman model."""
    _runtime_config["chairman_model"] = model
    save_settings()

def get_enhanced_features():
    """Get enhanced features config."""
    return _runtime_config["enhanced_features"]

def set_enhanced_features(features: dict):
    """Set enhanced features config."""
    _runtime_config["enhanced_features"].update(features)
    save_settings()

def get_presets():
    """Get all available council presets."""
    return COUNCIL_PRESETS

def apply_preset(preset_id: str):
    """Apply a preset configuration to the council."""
    if preset_id not in COUNCIL_PRESETS:
        raise ValueError(f"Invalid preset ID: {preset_id}")

    preset = COUNCIL_PRESETS[preset_id]
    set_council_models(preset["models"])
    set_chairman_model(preset["chairman"])

    return {
        "council_models": preset["models"],
        "chairman_model": preset["chairman"],
        "preset_name": preset["name"],
        "preset_description": preset["description"]
    }

# Load settings on module import
load_settings()

# OpenRouter API endpoint
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Perplexity API endpoint and defaults
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
DEFAULT_PERPLEXITY_SEARCH_MODEL = os.getenv(
    "PERPLEXITY_SEARCH_MODEL",
    "sonar"
)
DEFAULT_PERPLEXITY_DEEP_SEARCH_MODEL = os.getenv(
    "PERPLEXITY_DEEP_SEARCH_MODEL",
    "sonar-deep-research"
)

# Data directory for conversation storage
DATA_DIR = "data/conversations"

# Reasoning models that require special handling
REASONING_MODELS = [
    # OpenAI O-series
    "openai/o1", "openai/o1-mini", "openai/o1-pro",
    "openai/o3", "openai/o3-mini", "openai/o3-pro",
    "openai/o3-deep-research",
    "openai/o4-mini", "openai/o4-mini-deep-research",
    # DeepSeek R1
    "deepseek/deepseek-r1", "deepseek/deepseek-r1-0528",
    # Qwen thinking models
    "qwen/qwq-32b", "qwen/qwq-32b-preview",
    "qwen/qwen3-235b-a22b-thinking",
    # xAI Grok thinking
    "x-ai/grok-4.1-thinking",
    # Anthropic thinking
    "anthropic/claude-3.7-sonnet:thinking",
    # Other reasoning models
    "perplexity/sonar-reasoning-pro",
    "minimax/m2-reasoning",
    "moonshot/kimi-k2-thinking",
]

# Configuration for reasoning models
REASONING_MODEL_CONFIG = {
    "extended_timeout": 120,  # 2 minutes for reasoning
    "show_thinking": True,
    "max_thinking_tokens": 10000
}

def is_reasoning_model(model: str) -> bool:
    """Check if a model is a reasoning model."""
    return model in REASONING_MODELS

def get_personas():
    """Get all available personas (default + custom)."""
    return {
        "default": DEFAULT_PERSONAS,
        "custom": _runtime_config.get("custom_personas", {})
    }

def get_model_persona(model_id: str) -> str:
    """Get persona assigned to a model."""
    personas = _runtime_config.get("personas", {})
    persona_key = personas.get(model_id, "")

    if not persona_key:
        return ""

    # Check if it's a default persona key
    if persona_key in DEFAULT_PERSONAS:
        return DEFAULT_PERSONAS[persona_key]

    # Check if it's a custom persona ID
    custom_personas = _runtime_config.get("custom_personas", {})
    if persona_key in custom_personas:
        return custom_personas[persona_key]

    # Otherwise, treat it as custom text
    return persona_key

def set_model_persona(model_id: str, persona_key: str):
    """Set persona for a model."""
    if "personas" not in _runtime_config:
        _runtime_config["personas"] = {}
    _runtime_config["personas"][model_id] = persona_key
    save_settings()

def create_custom_persona(persona_id: str, persona_text: str):
    """Create a custom persona."""
    if "custom_personas" not in _runtime_config:
        _runtime_config["custom_personas"] = {}
    _runtime_config["custom_personas"][persona_id] = persona_text
    save_settings()
    return persona_id


def get_api_keys():
    """Get all configured API keys (masked for security)."""
    keys = _runtime_config.get("api_keys", {})
    # Add OpenRouter from env if not in config
    if not keys.get("openrouter") and _OPENROUTER_API_KEY_ENV:
        keys["openrouter"] = _OPENROUTER_API_KEY_ENV
    # Add Perplexity from env if not in config
    if not keys.get("perplexity") and _PERPLEXITY_API_KEY_ENV:
        keys["perplexity"] = _PERPLEXITY_API_KEY_ENV

    # Return masked versions for display
    masked = {}
    for provider, key in keys.items():
        if key:
            # Show first 4 and last 4 chars only
            if len(key) > 12:
                masked[provider] = f"{key[:4]}...{key[-4:]}"
            else:
                masked[provider] = "****"
        else:
            masked[provider] = ""
    return masked


def get_api_key(provider: str) -> str:
    """Get raw API key for a provider (for internal use)."""
    return _runtime_config.get("api_keys", {}).get(provider, "")


def set_api_key(provider: str, api_key: str):
    """Set API key for a provider."""
    if "api_keys" not in _runtime_config:
        _runtime_config["api_keys"] = {}
    _runtime_config["api_keys"][provider] = api_key
    save_settings()


def get_openrouter_api_key() -> str:
    """
    Get OpenRouter API key - checks Settings first, then environment variable.
    """
    # Check if set via Settings UI
    settings_key = _runtime_config.get("api_keys", {}).get("openrouter", "")
    if settings_key:
        return settings_key
    
    # Fallback to environment variable
    return _OPENROUTER_API_KEY_ENV


def get_perplexity_api_key() -> str:
    """Get Perplexity API key - checks Settings first, then env."""
    settings_key = _runtime_config.get("api_keys", {}).get("perplexity", "")
    if settings_key:
        return settings_key
    return _PERPLEXITY_API_KEY_ENV


def get_perplexity_models() -> dict:
    """Get configured Perplexity models for search and deep search."""
    return {
        "search": DEFAULT_PERPLEXITY_SEARCH_MODEL,
        "deep_search": DEFAULT_PERPLEXITY_DEEP_SEARCH_MODEL
    }


def get_provider_from_model(model_id: str) -> str:
    """Extract provider name from model ID (e.g., 'openai/gpt-4o' -> 'openai')."""
    return model_id.split('/')[0] if '/' in model_id else ""


def has_direct_api_key(model_id: str) -> bool:
    """Check if we have a direct API key for the model's provider."""
    provider = get_provider_from_model(model_id)
    return bool(get_api_key(provider))
