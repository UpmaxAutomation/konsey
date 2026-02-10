"""
Image Generation Module for LLM Council.

Provides image generation capabilities using various providers:
- OpenAI DALL-E 3
- Stability AI (Stable Diffusion)
- Together AI
- Replicate
"""

import asyncio
import aiohttp
import base64
import os
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

# Get API keys from environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
STABILITY_API_KEY = os.getenv("STABILITY_API_KEY", "")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")


class ImageProvider(str, Enum):
    DALLE_3 = "dalle-3"
    DALLE_2 = "dalle-2"
    STABLE_DIFFUSION_XL = "sdxl"
    STABLE_DIFFUSION_3 = "sd3"
    FLUX = "flux"


class ImageSize(str, Enum):
    SQUARE = "1024x1024"
    LANDSCAPE = "1792x1024"
    PORTRAIT = "1024x1792"


class ImageQuality(str, Enum):
    STANDARD = "standard"
    HD = "hd"


@dataclass
class GeneratedImage:
    """Represents a generated image."""
    id: str
    prompt: str
    provider: str
    size: str
    url: Optional[str] = None
    base64_data: Optional[str] = None
    revised_prompt: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    error: Optional[str] = None


# In-memory storage for generated images
_generated_images: Dict[str, GeneratedImage] = {}


async def generate_image_dalle(
    prompt: str,
    size: str = "1024x1024",
    quality: str = "standard",
    model: str = "dall-e-3",
    style: str = "vivid"
) -> GeneratedImage:
    """Generate image using OpenAI DALL-E."""
    image_id = str(uuid.uuid4())

    if not OPENAI_API_KEY:
        return GeneratedImage(
            id=image_id,
            prompt=prompt,
            provider=model,
            size=size,
            error="OpenAI API key not configured"
        )

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.openai.com/v1/images/generations",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "prompt": prompt,
                    "n": 1,
                    "size": size,
                    "quality": quality,
                    "style": style,
                    "response_format": "url"
                },
                timeout=aiohttp.ClientTimeout(total=120)
            ) as response:
                data = await response.json()

                if response.status != 200:
                    return GeneratedImage(
                        id=image_id,
                        prompt=prompt,
                        provider=model,
                        size=size,
                        error=data.get("error", {}).get("message", "Unknown error")
                    )

                image_data = data.get("data", [{}])[0]
                image = GeneratedImage(
                    id=image_id,
                    prompt=prompt,
                    provider=model,
                    size=size,
                    url=image_data.get("url"),
                    revised_prompt=image_data.get("revised_prompt")
                )
                _generated_images[image_id] = image
                return image

    except Exception as e:
        return GeneratedImage(
            id=image_id,
            prompt=prompt,
            provider=model,
            size=size,
            error=str(e)
        )


async def generate_image_stability(
    prompt: str,
    size: str = "1024x1024",
    model: str = "stable-diffusion-xl-1024-v1-0",
    cfg_scale: float = 7.0,
    steps: int = 30
) -> GeneratedImage:
    """Generate image using Stability AI."""
    image_id = str(uuid.uuid4())

    if not STABILITY_API_KEY:
        return GeneratedImage(
            id=image_id,
            prompt=prompt,
            provider=model,
            size=size,
            error="Stability API key not configured"
        )

    # Parse size
    width, height = map(int, size.split("x"))

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"https://api.stability.ai/v1/generation/{model}/text-to-image",
                headers={
                    "Authorization": f"Bearer {STABILITY_API_KEY}",
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                json={
                    "text_prompts": [{"text": prompt, "weight": 1}],
                    "cfg_scale": cfg_scale,
                    "height": height,
                    "width": width,
                    "steps": steps,
                    "samples": 1
                },
                timeout=aiohttp.ClientTimeout(total=120)
            ) as response:
                data = await response.json()

                if response.status != 200:
                    return GeneratedImage(
                        id=image_id,
                        prompt=prompt,
                        provider=model,
                        size=size,
                        error=data.get("message", "Unknown error")
                    )

                artifacts = data.get("artifacts", [])
                if artifacts:
                    image = GeneratedImage(
                        id=image_id,
                        prompt=prompt,
                        provider=model,
                        size=size,
                        base64_data=artifacts[0].get("base64")
                    )
                    _generated_images[image_id] = image
                    return image

                return GeneratedImage(
                    id=image_id,
                    prompt=prompt,
                    provider=model,
                    size=size,
                    error="No image generated"
                )

    except Exception as e:
        return GeneratedImage(
            id=image_id,
            prompt=prompt,
            provider=model,
            size=size,
            error=str(e)
        )


async def generate_image_together(
    prompt: str,
    size: str = "1024x1024",
    model: str = "stabilityai/stable-diffusion-xl-base-1.0",
    steps: int = 30
) -> GeneratedImage:
    """Generate image using Together AI."""
    image_id = str(uuid.uuid4())

    if not TOGETHER_API_KEY:
        return GeneratedImage(
            id=image_id,
            prompt=prompt,
            provider=model,
            size=size,
            error="Together API key not configured"
        )

    width, height = map(int, size.split("x"))

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.together.xyz/v1/images/generations",
                headers={
                    "Authorization": f"Bearer {TOGETHER_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "prompt": prompt,
                    "width": width,
                    "height": height,
                    "steps": steps,
                    "n": 1,
                    "response_format": "b64_json"
                },
                timeout=aiohttp.ClientTimeout(total=120)
            ) as response:
                data = await response.json()

                if response.status != 200:
                    return GeneratedImage(
                        id=image_id,
                        prompt=prompt,
                        provider=model,
                        size=size,
                        error=data.get("error", {}).get("message", "Unknown error")
                    )

                images = data.get("data", [])
                if images:
                    image = GeneratedImage(
                        id=image_id,
                        prompt=prompt,
                        provider=model,
                        size=size,
                        base64_data=images[0].get("b64_json")
                    )
                    _generated_images[image_id] = image
                    return image

                return GeneratedImage(
                    id=image_id,
                    prompt=prompt,
                    provider=model,
                    size=size,
                    error="No image generated"
                )

    except Exception as e:
        return GeneratedImage(
            id=image_id,
            prompt=prompt,
            provider=model,
            size=size,
            error=str(e)
        )


async def generate_image(
    prompt: str,
    provider: str = "dalle-3",
    size: str = "1024x1024",
    quality: str = "standard",
    **kwargs
) -> GeneratedImage:
    """
    Generate an image using the specified provider.

    Args:
        prompt: The text prompt for image generation
        provider: Provider to use (dalle-3, dalle-2, sdxl, sd3, flux)
        size: Image size (1024x1024, 1792x1024, 1024x1792)
        quality: Quality level (standard, hd)
        **kwargs: Additional provider-specific parameters

    Returns:
        GeneratedImage with URL or base64 data
    """
    if provider in ["dalle-3", "dall-e-3"]:
        return await generate_image_dalle(
            prompt=prompt,
            size=size,
            quality=quality,
            model="dall-e-3",
            **kwargs
        )
    elif provider in ["dalle-2", "dall-e-2"]:
        return await generate_image_dalle(
            prompt=prompt,
            size=size if size in ["256x256", "512x512", "1024x1024"] else "1024x1024",
            quality="standard",
            model="dall-e-2",
            **kwargs
        )
    elif provider in ["sdxl", "stable-diffusion-xl"]:
        return await generate_image_stability(
            prompt=prompt,
            size=size,
            model="stable-diffusion-xl-1024-v1-0",
            **kwargs
        )
    elif provider in ["sd3", "stable-diffusion-3"]:
        return await generate_image_stability(
            prompt=prompt,
            size=size,
            model="stable-diffusion-v3",
            **kwargs
        )
    elif provider in ["flux"]:
        return await generate_image_together(
            prompt=prompt,
            size=size,
            model="black-forest-labs/FLUX.1-schnell-Free",
            **kwargs
        )
    elif provider in ["together-sdxl"]:
        return await generate_image_together(
            prompt=prompt,
            size=size,
            model="stabilityai/stable-diffusion-xl-base-1.0",
            **kwargs
        )
    else:
        # Default to DALL-E 3
        return await generate_image_dalle(
            prompt=prompt,
            size=size,
            quality=quality,
            model="dall-e-3",
            **kwargs
        )


def get_image(image_id: str) -> Optional[GeneratedImage]:
    """Get a generated image by ID."""
    return _generated_images.get(image_id)


def list_images(limit: int = 50) -> List[Dict[str, Any]]:
    """List all generated images."""
    images = list(_generated_images.values())
    images.sort(key=lambda x: x.created_at, reverse=True)
    return [
        {
            "id": img.id,
            "prompt": img.prompt,
            "provider": img.provider,
            "size": img.size,
            "url": img.url,
            "has_base64": img.base64_data is not None,
            "revised_prompt": img.revised_prompt,
            "created_at": img.created_at,
            "error": img.error
        }
        for img in images[:limit]
    ]


def delete_image(image_id: str) -> bool:
    """Delete a generated image."""
    if image_id in _generated_images:
        del _generated_images[image_id]
        return True
    return False


def get_available_providers() -> List[Dict[str, Any]]:
    """Get list of available image generation providers."""
    return [
        {
            "id": "dalle-3",
            "name": "DALL-E 3",
            "provider": "OpenAI",
            "available": bool(OPENAI_API_KEY),
            "sizes": ["1024x1024", "1792x1024", "1024x1792"],
            "qualities": ["standard", "hd"],
            "styles": ["vivid", "natural"]
        },
        {
            "id": "dalle-2",
            "name": "DALL-E 2",
            "provider": "OpenAI",
            "available": bool(OPENAI_API_KEY),
            "sizes": ["256x256", "512x512", "1024x1024"],
            "qualities": ["standard"]
        },
        {
            "id": "sdxl",
            "name": "Stable Diffusion XL",
            "provider": "Stability AI",
            "available": bool(STABILITY_API_KEY),
            "sizes": ["1024x1024", "1152x896", "896x1152"],
            "qualities": ["standard"]
        },
        {
            "id": "flux",
            "name": "FLUX.1",
            "provider": "Together AI",
            "available": bool(TOGETHER_API_KEY),
            "sizes": ["1024x1024", "1024x768", "768x1024"],
            "qualities": ["standard"]
        },
        {
            "id": "together-sdxl",
            "name": "SDXL (Together)",
            "provider": "Together AI",
            "available": bool(TOGETHER_API_KEY),
            "sizes": ["1024x1024", "1024x768", "768x1024"],
            "qualities": ["standard"]
        }
    ]


def image_to_dict(image: GeneratedImage) -> Dict[str, Any]:
    """Convert GeneratedImage to dictionary."""
    return {
        "id": image.id,
        "prompt": image.prompt,
        "provider": image.provider,
        "size": image.size,
        "url": image.url,
        "base64_data": image.base64_data,
        "revised_prompt": image.revised_prompt,
        "created_at": image.created_at,
        "error": image.error
    }
