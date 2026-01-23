"""Tests for Image Generation module."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


class TestImageProvider:
    """Tests for ImageProvider enum."""

    def test_provider_values(self):
        from image_gen import ImageProvider

        assert ImageProvider.DALLE_3.value == "dalle-3"
        assert ImageProvider.DALLE_2.value == "dalle-2"
        assert ImageProvider.STABLE_DIFFUSION_XL.value == "sdxl"
        assert ImageProvider.FLUX.value == "flux"


class TestImageSize:
    """Tests for ImageSize enum."""

    def test_size_values(self):
        from image_gen import ImageSize

        assert ImageSize.SQUARE.value == "1024x1024"
        assert ImageSize.LANDSCAPE.value == "1792x1024"
        assert ImageSize.PORTRAIT.value == "1024x1792"


class TestGeneratedImage:
    """Tests for GeneratedImage dataclass."""

    def test_image_creation(self):
        from image_gen import GeneratedImage

        image = GeneratedImage(
            id="img-1",
            prompt="A cat",
            provider="dalle-3",
            size="1024x1024"
        )

        assert image.id == "img-1"
        assert image.prompt == "A cat"
        assert image.url is None
        assert image.error is None

    def test_image_with_error(self):
        from image_gen import GeneratedImage

        image = GeneratedImage(
            id="img-2",
            prompt="Test",
            provider="dalle-3",
            size="1024x1024",
            error="API key not configured"
        )

        assert image.error == "API key not configured"


class TestGenerateImageDalle:
    """Tests for generate_image_dalle function."""

    @pytest.mark.asyncio
    async def test_missing_api_key(self):
        from image_gen import generate_image_dalle

        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}):
            # Reload module to pick up new env
            import importlib
            import image_gen
            importlib.reload(image_gen)

            result = await image_gen.generate_image_dalle("A cat")

            assert result.error is not None
            assert "API key" in result.error

    @pytest.mark.asyncio
    async def test_successful_generation(self):
        from image_gen import generate_image_dalle, _generated_images

        _generated_images.clear()

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "data": [{
                "url": "https://example.com/image.png",
                "revised_prompt": "A cute cat"
            }]
        })

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            with patch("aiohttp.ClientSession") as mock_session:
                mock_session.return_value.__aenter__ = AsyncMock(
                    return_value=MagicMock(
                        post=MagicMock(return_value=AsyncMock(
                            __aenter__=AsyncMock(return_value=mock_response),
                            __aexit__=AsyncMock()
                        ))
                    )
                )
                mock_session.return_value.__aexit__ = AsyncMock()

                import importlib
                import image_gen
                importlib.reload(image_gen)

                result = await image_gen.generate_image_dalle("A cat")

                assert result.url == "https://example.com/image.png"
                assert result.revised_prompt == "A cute cat"


class TestGenerateImage:
    """Tests for generate_image function (router)."""

    @pytest.mark.asyncio
    async def test_dalle3_routing(self):
        with patch("image_gen.generate_image_dalle") as mock_dalle:
            mock_dalle.return_value = MagicMock()

            from image_gen import generate_image
            await generate_image("test", provider="dalle-3")

            mock_dalle.assert_called_once()

    @pytest.mark.asyncio
    async def test_flux_routing(self):
        with patch("image_gen.generate_image_together") as mock_together:
            mock_together.return_value = MagicMock()

            from image_gen import generate_image
            await generate_image("test", provider="flux")

            mock_together.assert_called_once()


class TestImageStorage:
    """Tests for image storage functions."""

    def test_get_image(self):
        from image_gen import get_image, _generated_images, GeneratedImage

        _generated_images.clear()
        image = GeneratedImage(id="img-1", prompt="test", provider="dalle-3", size="1024x1024")
        _generated_images["img-1"] = image

        result = get_image("img-1")
        assert result == image

        result = get_image("nonexistent")
        assert result is None

    def test_list_images(self):
        from image_gen import list_images, _generated_images, GeneratedImage

        _generated_images.clear()
        _generated_images["img-1"] = GeneratedImage(
            id="img-1", prompt="test1", provider="dalle-3", size="1024x1024"
        )
        _generated_images["img-2"] = GeneratedImage(
            id="img-2", prompt="test2", provider="sdxl", size="1024x1024"
        )

        result = list_images()
        assert len(result) == 2

    def test_delete_image(self):
        from image_gen import delete_image, _generated_images, GeneratedImage

        _generated_images.clear()
        _generated_images["img-1"] = GeneratedImage(
            id="img-1", prompt="test", provider="dalle-3", size="1024x1024"
        )

        result = delete_image("img-1")
        assert result is True
        assert "img-1" not in _generated_images


class TestGetAvailableProviders:
    """Tests for get_available_providers function."""

    def test_providers_structure(self):
        from image_gen import get_available_providers

        providers = get_available_providers()

        assert len(providers) >= 4
        assert all("id" in p for p in providers)
        assert all("name" in p for p in providers)
        assert all("available" in p for p in providers)

    def test_dalle3_provider(self):
        from image_gen import get_available_providers

        providers = get_available_providers()
        dalle3 = next(p for p in providers if p["id"] == "dalle-3")

        assert dalle3["name"] == "DALL-E 3"
        assert dalle3["provider"] == "OpenAI"
        assert "1024x1024" in dalle3["sizes"]


class TestImageToDict:
    """Tests for image_to_dict function."""

    def test_image_to_dict(self):
        from image_gen import image_to_dict, GeneratedImage

        image = GeneratedImage(
            id="img-1",
            prompt="A sunset",
            provider="dalle-3",
            size="1024x1024",
            url="https://example.com/image.png",
            revised_prompt="A beautiful sunset"
        )

        result = image_to_dict(image)

        assert result["id"] == "img-1"
        assert result["prompt"] == "A sunset"
        assert result["url"] == "https://example.com/image.png"
        assert result["revised_prompt"] == "A beautiful sunset"
