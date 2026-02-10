"""Tests for Voice TTS/STT module."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


class TestTTSProvider:
    """Tests for TTSProvider enum."""

    def test_provider_values(self):
        from voice import TTSProvider

        assert TTSProvider.OPENAI.value == "openai"
        assert TTSProvider.ELEVENLABS.value == "elevenlabs"


class TestSTTProvider:
    """Tests for STTProvider enum."""

    def test_provider_values(self):
        from voice import STTProvider

        assert STTProvider.OPENAI_WHISPER.value == "whisper"
        assert STTProvider.ASSEMBLYAI.value == "assemblyai"


class TestTTSVoice:
    """Tests for TTSVoice enum."""

    def test_voice_values(self):
        from voice import TTSVoice

        assert TTSVoice.ALLOY.value == "alloy"
        assert TTSVoice.ECHO.value == "echo"
        assert TTSVoice.NOVA.value == "nova"


class TestTTSResult:
    """Tests for TTSResult dataclass."""

    def test_result_creation(self):
        from voice import TTSResult

        result = TTSResult(
            id="tts-1",
            text="Hello world",
            provider="openai",
            voice="alloy"
        )

        assert result.id == "tts-1"
        assert result.text == "Hello world"
        assert result.audio_base64 is None
        assert result.error is None

    def test_result_with_audio(self):
        from voice import TTSResult

        result = TTSResult(
            id="tts-2",
            text="Test",
            provider="openai",
            voice="echo",
            audio_base64="base64data=="
        )

        assert result.audio_base64 == "base64data=="


class TestTranscriptionResult:
    """Tests for TranscriptionResult dataclass."""

    def test_result_creation(self):
        from voice import TranscriptionResult

        result = TranscriptionResult(
            id="stt-1",
            provider="whisper",
            text="Transcribed text"
        )

        assert result.id == "stt-1"
        assert result.text == "Transcribed text"
        assert result.language is None

    def test_result_with_metadata(self):
        from voice import TranscriptionResult

        result = TranscriptionResult(
            id="stt-2",
            provider="assemblyai",
            text="Hello",
            language="en",
            duration_seconds=3.5,
            confidence=0.95
        )

        assert result.language == "en"
        assert result.duration_seconds == 3.5
        assert result.confidence == 0.95


class TestTextToSpeechOpenAI:
    """Tests for text_to_speech_openai function."""

    @pytest.mark.asyncio
    async def test_missing_api_key(self):
        from voice import text_to_speech_openai

        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}):
            import importlib
            import voice
            importlib.reload(voice)

            result = await voice.text_to_speech_openai("Hello")

            assert result.error is not None
            assert "API key" in result.error

    @pytest.mark.asyncio
    async def test_successful_tts(self):
        import base64
        from voice import _tts_results

        _tts_results.clear()

        audio_data = b"fake audio data"
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.read = AsyncMock(return_value=audio_data)

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
                import voice
                importlib.reload(voice)

                result = await voice.text_to_speech_openai("Hello world")

                expected_base64 = base64.b64encode(audio_data).decode('utf-8')
                assert result.audio_base64 == expected_base64
                assert result.error is None


class TestTextToSpeech:
    """Tests for text_to_speech function (router)."""

    @pytest.mark.asyncio
    async def test_openai_routing(self):
        with patch("voice.text_to_speech_openai") as mock_openai:
            mock_openai.return_value = MagicMock()

            from voice import text_to_speech
            await text_to_speech("test", provider="openai")

            mock_openai.assert_called_once()

    @pytest.mark.asyncio
    async def test_elevenlabs_routing(self):
        with patch("voice.text_to_speech_elevenlabs") as mock_eleven:
            mock_eleven.return_value = MagicMock()

            from voice import text_to_speech
            await text_to_speech("test", provider="elevenlabs")

            mock_eleven.assert_called_once()


class TestTranscribeOpenAI:
    """Tests for transcribe_openai function."""

    @pytest.mark.asyncio
    async def test_missing_api_key(self):
        from voice import transcribe_openai

        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}):
            import importlib
            import voice
            importlib.reload(voice)

            result = await voice.transcribe_openai(b"audio data")

            assert result.error is not None
            assert "API key" in result.error


class TestTranscribe:
    """Tests for transcribe function (router)."""

    @pytest.mark.asyncio
    async def test_whisper_routing(self):
        with patch("voice.transcribe_openai") as mock_whisper:
            mock_whisper.return_value = MagicMock()

            from voice import transcribe
            await transcribe(b"audio", provider="whisper")

            mock_whisper.assert_called_once()

    @pytest.mark.asyncio
    async def test_assemblyai_routing(self):
        with patch("voice.transcribe_assemblyai") as mock_assembly:
            mock_assembly.return_value = MagicMock()

            from voice import transcribe
            await transcribe(b"audio", provider="assemblyai")

            mock_assembly.assert_called_once()


class TestTTSStorage:
    """Tests for TTS result storage functions."""

    def test_get_tts_result(self):
        from voice import get_tts_result, _tts_results, TTSResult

        _tts_results.clear()
        result = TTSResult(id="tts-1", text="test", provider="openai", voice="alloy")
        _tts_results["tts-1"] = result

        fetched = get_tts_result("tts-1")
        assert fetched == result

        fetched = get_tts_result("nonexistent")
        assert fetched is None

    def test_list_tts_results(self):
        from voice import list_tts_results, _tts_results, TTSResult

        _tts_results.clear()
        _tts_results["tts-1"] = TTSResult(id="tts-1", text="test1", provider="openai", voice="alloy")
        _tts_results["tts-2"] = TTSResult(id="tts-2", text="test2", provider="openai", voice="echo")

        results = list_tts_results()
        assert len(results) == 2


class TestTranscriptionStorage:
    """Tests for transcription result storage functions."""

    def test_get_transcription_result(self):
        from voice import get_transcription_result, _transcription_results, TranscriptionResult

        _transcription_results.clear()
        result = TranscriptionResult(id="stt-1", provider="whisper", text="Hello")
        _transcription_results["stt-1"] = result

        fetched = get_transcription_result("stt-1")
        assert fetched == result

    def test_list_transcriptions(self):
        from voice import list_transcriptions, _transcription_results, TranscriptionResult

        _transcription_results.clear()
        _transcription_results["stt-1"] = TranscriptionResult(id="stt-1", provider="whisper", text="test1")
        _transcription_results["stt-2"] = TranscriptionResult(id="stt-2", provider="assemblyai", text="test2")

        results = list_transcriptions()
        assert len(results) == 2


class TestGetAvailableTTSProviders:
    """Tests for get_available_tts_providers function."""

    def test_providers_structure(self):
        from voice import get_available_tts_providers

        providers = get_available_tts_providers()

        assert len(providers) >= 2
        assert all("id" in p for p in providers)
        assert all("name" in p for p in providers)
        assert all("available" in p for p in providers)
        assert all("voices" in p for p in providers)

    def test_openai_provider(self):
        from voice import get_available_tts_providers

        providers = get_available_tts_providers()
        openai = next(p for p in providers if p["id"] == "openai")

        assert openai["name"] == "OpenAI TTS"
        assert len(openai["voices"]) == 6


class TestGetAvailableSTTProviders:
    """Tests for get_available_stt_providers function."""

    def test_providers_structure(self):
        from voice import get_available_stt_providers

        providers = get_available_stt_providers()

        assert len(providers) >= 2
        assert all("id" in p for p in providers)
        assert all("name" in p for p in providers)
        assert all("available" in p for p in providers)

    def test_whisper_provider(self):
        from voice import get_available_stt_providers

        providers = get_available_stt_providers()
        whisper = next(p for p in providers if p["id"] == "whisper")

        assert whisper["name"] == "OpenAI Whisper"
        assert "Word-level timestamps" in whisper["features"]


class TestResultToDict:
    """Tests for result conversion functions."""

    def test_tts_result_to_dict(self):
        from voice import tts_result_to_dict, TTSResult

        result = TTSResult(
            id="tts-1",
            text="Hello world",
            provider="openai",
            voice="alloy",
            audio_base64="base64data=="
        )

        d = tts_result_to_dict(result)

        assert d["id"] == "tts-1"
        assert d["text"] == "Hello world"
        assert d["provider"] == "openai"
        assert d["audio_base64"] == "base64data=="

    def test_transcription_result_to_dict(self):
        from voice import transcription_result_to_dict, TranscriptionResult

        result = TranscriptionResult(
            id="stt-1",
            provider="whisper",
            text="Transcribed text",
            language="en",
            duration_seconds=5.0
        )

        d = transcription_result_to_dict(result)

        assert d["id"] == "stt-1"
        assert d["text"] == "Transcribed text"
        assert d["language"] == "en"
        assert d["duration_seconds"] == 5.0
