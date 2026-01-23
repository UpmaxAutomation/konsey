"""Direct API clients for provider-native connections (bypassing OpenRouter)."""

import httpx
import json
from typing import List, Dict, Any, Optional
from .config import (
    get_api_key, get_provider_from_model, PROVIDER_API_ENDPOINTS,
    AVAILABLE_MODELS, is_reasoning_model, REASONING_MODEL_CONFIG
)


async def query_openai_direct(
    model_id: str,
    messages: List[Dict[str, str]],
    api_key: str,
    timeout: float = 120.0
) -> Optional[Dict[str, Any]]:
    """Query OpenAI API directly."""
    # Extract model name (e.g., 'openai/gpt-4o' -> 'gpt-4o')
    model_name = model_id.split('/')[-1] if '/' in model_id else model_id

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model_name,
        "messages": messages,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                PROVIDER_API_ENDPOINTS["openai"],
                headers=headers,
                json=payload
            )
            response.raise_for_status()

            data = response.json()
            message = data['choices'][0]['message']
            usage = data.get('usage', {})

            return {
                'content': message.get('content'),
                'usage': {
                    'input_tokens': usage.get('prompt_tokens', 0),
                    'output_tokens': usage.get('completion_tokens', 0),
                },
                'provider': 'openai_direct'
            }
    except Exception as e:
        print(f"Error querying OpenAI directly: {e}")
        return None


async def query_anthropic_direct(
    model_id: str,
    messages: List[Dict[str, str]],
    api_key: str,
    timeout: float = 120.0
) -> Optional[Dict[str, Any]]:
    """Query Anthropic API directly."""
    # Extract model name (e.g., 'anthropic/claude-sonnet-4' -> 'claude-sonnet-4')
    model_name = model_id.split('/')[-1] if '/' in model_id else model_id

    # Map friendly names to actual API model names
    model_mapping = {
        "claude-opus-4.5": "claude-opus-4-5-20250514",
        "claude-opus-4": "claude-opus-4-20250514",
        "claude-sonnet-4": "claude-sonnet-4-20250514",
        "claude-3.5-haiku": "claude-3-5-haiku-20241022",
        "claude-3-haiku": "claude-3-haiku-20240307",
    }
    api_model = model_mapping.get(model_name, model_name)

    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01",
    }

    # Convert messages format for Anthropic
    # Anthropic expects system message separately
    system_content = ""
    anthropic_messages = []

    for msg in messages:
        if msg['role'] == 'system':
            system_content = msg['content']
        else:
            anthropic_messages.append({
                'role': msg['role'],
                'content': msg['content']
            })

    payload = {
        "model": api_model,
        "max_tokens": 4096,
        "messages": anthropic_messages,
    }

    if system_content:
        payload["system"] = system_content

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                PROVIDER_API_ENDPOINTS["anthropic"],
                headers=headers,
                json=payload
            )
            response.raise_for_status()

            data = response.json()
            content = ""
            if data.get('content'):
                for block in data['content']:
                    if block.get('type') == 'text':
                        content += block.get('text', '')

            usage = data.get('usage', {})

            return {
                'content': content,
                'usage': {
                    'input_tokens': usage.get('input_tokens', 0),
                    'output_tokens': usage.get('output_tokens', 0),
                },
                'provider': 'anthropic_direct'
            }
    except Exception as e:
        print(f"Error querying Anthropic directly: {e}")
        return None


async def query_google_direct(
    model_id: str,
    messages: List[Dict[str, str]],
    api_key: str,
    timeout: float = 120.0
) -> Optional[Dict[str, Any]]:
    """Query Google Gemini API directly."""
    # Extract model name
    model_name = model_id.split('/')[-1] if '/' in model_id else model_id

    # Map to Gemini API model names
    model_mapping = {
        "gemini-2.5-pro": "gemini-2.5-pro-preview-06-05",
        "gemini-2.5-flash": "gemini-2.5-flash-preview-05-20",
        "gemini-2.0-flash": "gemini-2.0-flash",
        "gemini-2.0-flash-lite": "gemini-2.0-flash-lite",
        "gemini-3-flash-preview": "gemini-3.0-flash-preview",
        "gemini-3-pro-preview": "gemini-3.0-pro-preview",
    }
    api_model = model_mapping.get(model_name, model_name)

    url = f"{PROVIDER_API_ENDPOINTS['google']}/{api_model}:generateContent?key={api_key}"

    # Convert to Gemini format
    contents = []
    system_instruction = None

    for msg in messages:
        if msg['role'] == 'system':
            system_instruction = {"parts": [{"text": msg['content']}]}
        else:
            role = "user" if msg['role'] == 'user' else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg['content']}]
            })

    payload = {
        "contents": contents,
        "generationConfig": {
            "maxOutputTokens": 4096,
        }
    }

    if system_instruction:
        payload["systemInstruction"] = system_instruction

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()

            data = response.json()

            content = ""
            if data.get('candidates'):
                candidate = data['candidates'][0]
                if candidate.get('content', {}).get('parts'):
                    content = candidate['content']['parts'][0].get('text', '')

            usage = data.get('usageMetadata', {})

            return {
                'content': content,
                'usage': {
                    'input_tokens': usage.get('promptTokenCount', 0),
                    'output_tokens': usage.get('candidatesTokenCount', 0),
                },
                'provider': 'google_direct'
            }
    except Exception as e:
        print(f"Error querying Google directly: {e}")
        return None


async def query_deepseek_direct(
    model_id: str,
    messages: List[Dict[str, str]],
    api_key: str,
    timeout: float = 120.0
) -> Optional[Dict[str, Any]]:
    """Query DeepSeek API directly (OpenAI-compatible)."""
    model_name = model_id.split('/')[-1] if '/' in model_id else model_id

    # Map to DeepSeek API model names
    model_mapping = {
        "deepseek-chat-v3": "deepseek-chat",
        "deepseek-r1": "deepseek-reasoner",
        "deepseek-r1-0528": "deepseek-reasoner",
    }
    api_model = model_mapping.get(model_name, model_name)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": api_model,
        "messages": messages,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                PROVIDER_API_ENDPOINTS["deepseek"],
                headers=headers,
                json=payload
            )
            response.raise_for_status()

            data = response.json()
            message = data['choices'][0]['message']
            usage = data.get('usage', {})

            result = {
                'content': message.get('content'),
                'usage': {
                    'input_tokens': usage.get('prompt_tokens', 0),
                    'output_tokens': usage.get('completion_tokens', 0),
                },
                'provider': 'deepseek_direct'
            }

            # Extract reasoning content for R1 models
            if message.get('reasoning_content'):
                result['thinking'] = message['reasoning_content']

            return result
    except Exception as e:
        print(f"Error querying DeepSeek directly: {e}")
        return None


async def query_xai_direct(
    model_id: str,
    messages: List[Dict[str, str]],
    api_key: str,
    timeout: float = 120.0
) -> Optional[Dict[str, Any]]:
    """Query xAI (Grok) API directly (OpenAI-compatible)."""
    model_name = model_id.split('/')[-1] if '/' in model_id else model_id

    # Map to xAI API model names
    model_mapping = {
        "grok-3": "grok-3",
        "grok-3-mini": "grok-3-mini",
        "grok-3-fast": "grok-3-fast",
        "grok-4.1-fast": "grok-4.1-fast",
    }
    api_model = model_mapping.get(model_name, model_name)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": api_model,
        "messages": messages,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                PROVIDER_API_ENDPOINTS["x-ai"],
                headers=headers,
                json=payload
            )
            response.raise_for_status()

            data = response.json()
            message = data['choices'][0]['message']
            usage = data.get('usage', {})

            return {
                'content': message.get('content'),
                'usage': {
                    'input_tokens': usage.get('prompt_tokens', 0),
                    'output_tokens': usage.get('completion_tokens', 0),
                },
                'provider': 'xai_direct'
            }
    except Exception as e:
        print(f"Error querying xAI directly: {e}")
        return None


async def query_mistral_direct(
    model_id: str,
    messages: List[Dict[str, str]],
    api_key: str,
    timeout: float = 120.0
) -> Optional[Dict[str, Any]]:
    """Query Mistral API directly (OpenAI-compatible)."""
    model_name = model_id.split('/')[-1] if '/' in model_id else model_id

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model_name,
        "messages": messages,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                PROVIDER_API_ENDPOINTS["mistralai"],
                headers=headers,
                json=payload
            )
            response.raise_for_status()

            data = response.json()
            message = data['choices'][0]['message']
            usage = data.get('usage', {})

            return {
                'content': message.get('content'),
                'usage': {
                    'input_tokens': usage.get('prompt_tokens', 0),
                    'output_tokens': usage.get('completion_tokens', 0),
                },
                'provider': 'mistral_direct'
            }
    except Exception as e:
        print(f"Error querying Mistral directly: {e}")
        return None


async def query_cohere_direct(
    model_id: str,
    messages: List[Dict[str, str]],
    api_key: str,
    timeout: float = 120.0
) -> Optional[Dict[str, Any]]:
    """Query Cohere API directly."""
    model_name = model_id.split('/')[-1] if '/' in model_id else model_id

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # Convert to Cohere format
    chat_history = []
    message_text = ""
    preamble = ""

    for msg in messages:
        if msg['role'] == 'system':
            preamble = msg['content']
        elif msg['role'] == 'user':
            if message_text:  # Previous user message becomes history
                chat_history.append({"role": "USER", "message": message_text})
            message_text = msg['content']
        elif msg['role'] == 'assistant':
            chat_history.append({"role": "CHATBOT", "message": msg['content']})

    payload = {
        "model": model_name,
        "message": message_text,
    }

    if chat_history:
        payload["chat_history"] = chat_history
    if preamble:
        payload["preamble"] = preamble

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                PROVIDER_API_ENDPOINTS["cohere"],
                headers=headers,
                json=payload
            )
            response.raise_for_status()

            data = response.json()

            return {
                'content': data.get('text', ''),
                'usage': {
                    'input_tokens': data.get('meta', {}).get('billed_units', {}).get('input_tokens', 0),
                    'output_tokens': data.get('meta', {}).get('billed_units', {}).get('output_tokens', 0),
                },
                'provider': 'cohere_direct'
            }
    except Exception as e:
        print(f"Error querying Cohere directly: {e}")
        return None


async def query_qwen_direct(
    model_id: str,
    messages: List[Dict[str, str]],
    api_key: str,
    timeout: float = 120.0
) -> Optional[Dict[str, Any]]:
    """Query Qwen (Alibaba DashScope) API directly (OpenAI-compatible)."""
    model_name = model_id.split('/')[-1] if '/' in model_id else model_id

    # Map to DashScope API model names
    model_mapping = {
        "qwen-2.5-72b-instruct": "qwen-plus",
        "qwen-2.5-coder-32b-instruct": "qwen-coder-plus",
        "qwq-32b": "qwq-32b-preview",
    }
    api_model = model_mapping.get(model_name, model_name)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": api_model,
        "messages": messages,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                PROVIDER_API_ENDPOINTS["qwen"],
                headers=headers,
                json=payload
            )
            response.raise_for_status()

            data = response.json()
            message = data['choices'][0]['message']
            usage = data.get('usage', {})

            result = {
                'content': message.get('content'),
                'usage': {
                    'input_tokens': usage.get('prompt_tokens', 0),
                    'output_tokens': usage.get('completion_tokens', 0),
                },
                'provider': 'qwen_direct'
            }

            # Extract reasoning content for QwQ models
            if message.get('reasoning_content'):
                result['thinking'] = message['reasoning_content']

            return result
    except Exception as e:
        print(f"Error querying Qwen directly: {e}")
        return None


# Provider query function mapping
PROVIDER_QUERY_FUNCTIONS = {
    "openai": query_openai_direct,
    "anthropic": query_anthropic_direct,
    "google": query_google_direct,
    "deepseek": query_deepseek_direct,
    "x-ai": query_xai_direct,
    "mistralai": query_mistral_direct,
    "cohere": query_cohere_direct,
    "qwen": query_qwen_direct,
}


async def query_model_direct(
    model_id: str,
    messages: List[Dict[str, str]],
    timeout: float = 120.0,
    api_key: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Query a model using direct provider API if API key is available.

    Args:
        model_id: Full model ID (e.g., 'openai/gpt-4o')
        messages: List of message dicts
        timeout: Request timeout in seconds
        api_key: Optional API key (if not provided, uses global config)

    Returns:
        Response dict with 'content', 'usage', 'provider' or None if failed
    """
    provider = get_provider_from_model(model_id)
    if not api_key:
        api_key = get_api_key(provider)

    if not api_key:
        return None

    if provider not in PROVIDER_QUERY_FUNCTIONS:
        print(f"No direct query function for provider: {provider}")
        return None

    # Use extended timeout for reasoning models
    if is_reasoning_model(model_id):
        timeout = REASONING_MODEL_CONFIG["extended_timeout"]

    query_func = PROVIDER_QUERY_FUNCTIONS[provider]
    return await query_func(model_id, messages, api_key, timeout)
