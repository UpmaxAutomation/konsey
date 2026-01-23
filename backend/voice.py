"""
Voice Module for LLM Council.

Provides text-to-speech and speech-to-text capabilities:
- TTS: OpenAI, ElevenLabs, Google Cloud
- STT: OpenAI Whisper, Google Cloud, AssemblyAI
"""

import asyncio
import aiohttp
import base64
import os
import uuid
import tempfile
from datetime import datetime
from typing import Dict, Any, List, Optional, BinaryIO
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY", "")


class TTSProvider(str, Enum):
    OPENAI = "openai"
    ELEVENLABS = "elevenlabs"


class STTProvider(str, Enum):
    OPENAI_WHISPER = "whisper"
    ASSEMBLYAI = "assemblyai"


class TTSVoice(str, Enum):
    # OpenAI voices
    ALLOY = "alloy"
    ECHO = "echo"
    FABLE = "fable"
    ONYX = "onyx"
    NOVA = "nova"
    SHIMMER = "shimmer"


@dataclass
class TTSResult:
    """Result from text-to-speech conversion."""
    id: str
    text: str
    provider: str
    voice: str
    audio_base64: Optional[str] = None
    audio_url: Optional[str] = None
    duration_seconds: Optional[float] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    error: Optional[str] = None


@dataclass
class TranscriptionResult:
    """Result from speech-to-text transcription."""
    id: str
    provider: str
    text: str
    language: Optional[str] = None
    duration_seconds: Optional[float] = None
    confidence: Optional[float] = None
    words: Optional[List[Dict[str, Any]]] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    error: Optional[str] = None


# Storage for results
_tts_results: Dict[str, TTSResult] = {}
_transcription_results: Dict[str, TranscriptionResult] = {}


async def text_to_speech_openai(
    text: str,
    voice: str = "alloy",
    model: str = "tts-1",
    speed: float = 1.0
) -> TTSResult:
    """Convert text to speech using OpenAI TTS."""
    result_id = str(uuid.uuid4())

    if not OPENAI_API_KEY:
        return TTSResult(
            id=result_id,
            text=text,
            provider="openai",
            voice=voice,
            error="OpenAI API key not configured"
        )

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.openai.com/v1/audio/speech",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "input": text,
                    "voice": voice,
                    "speed": speed,
                    "response_format": "mp3"
                },
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status != 200:
                    error_data = await response.json()
                    return TTSResult(
                        id=result_id,
                        text=text,
                        provider="openai",
                        voice=voice,
                        error=error_data.get("error", {}).get("message", "Unknown error")
                    )

                audio_data = await response.read()
                audio_base64 = base64.b64encode(audio_data).decode('utf-8')

                result = TTSResult(
                    id=result_id,
                    text=text,
                    provider="openai",
                    voice=voice,
                    audio_base64=audio_base64
                )
                _tts_results[result_id] = result
                return result

    except Exception as e:
        return TTSResult(
            id=result_id,
            text=text,
            provider="openai",
            voice=voice,
            error=str(e)
        )


async def text_to_speech_elevenlabs(
    text: str,
    voice_id: str = "21m00Tcm4TlvDq8ikWAM",  # Rachel
    model_id: str = "eleven_monolingual_v1",
    stability: float = 0.5,
    similarity_boost: float = 0.75
) -> TTSResult:
    """Convert text to speech using ElevenLabs."""
    result_id = str(uuid.uuid4())

    if not ELEVENLABS_API_KEY:
        return TTSResult(
            id=result_id,
            text=text,
            provider="elevenlabs",
            voice=voice_id,
            error="ElevenLabs API key not configured"
        )

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers={
                    "xi-api-key": ELEVENLABS_API_KEY,
                    "Content-Type": "application/json",
                    "Accept": "audio/mpeg"
                },
                json={
                    "text": text,
                    "model_id": model_id,
                    "voice_settings": {
                        "stability": stability,
                        "similarity_boost": similarity_boost
                    }
                },
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    return TTSResult(
                        id=result_id,
                        text=text,
                        provider="elevenlabs",
                        voice=voice_id,
                        error=error_text
                    )

                audio_data = await response.read()
                audio_base64 = base64.b64encode(audio_data).decode('utf-8')

                result = TTSResult(
                    id=result_id,
                    text=text,
                    provider="elevenlabs",
                    voice=voice_id,
                    audio_base64=audio_base64
                )
                _tts_results[result_id] = result
                return result

    except Exception as e:
        return TTSResult(
            id=result_id,
            text=text,
            provider="elevenlabs",
            voice=voice_id,
            error=str(e)
        )


async def text_to_speech(
    text: str,
    provider: str = "openai",
    voice: str = "alloy",
    **kwargs
) -> TTSResult:
    """
    Convert text to speech using the specified provider.

    Args:
        text: Text to convert to speech
        provider: TTS provider (openai, elevenlabs)
        voice: Voice to use
        **kwargs: Additional provider-specific parameters

    Returns:
        TTSResult with audio data
    """
    if provider == "openai":
        return await text_to_speech_openai(text, voice=voice, **kwargs)
    elif provider == "elevenlabs":
        return await text_to_speech_elevenlabs(text, voice_id=voice, **kwargs)
    else:
        return await text_to_speech_openai(text, voice=voice, **kwargs)


async def transcribe_openai(
    audio_data: bytes,
    filename: str = "audio.mp3",
    language: Optional[str] = None,
    prompt: Optional[str] = None
) -> TranscriptionResult:
    """Transcribe audio using OpenAI Whisper."""
    result_id = str(uuid.uuid4())

    if not OPENAI_API_KEY:
        return TranscriptionResult(
            id=result_id,
            provider="whisper",
            text="",
            error="OpenAI API key not configured"
        )

    try:
        # Create form data
        form = aiohttp.FormData()
        form.add_field('file', audio_data, filename=filename, content_type='audio/mpeg')
        form.add_field('model', 'whisper-1')
        form.add_field('response_format', 'verbose_json')

        if language:
            form.add_field('language', language)
        if prompt:
            form.add_field('prompt', prompt)

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}"
                },
                data=form,
                timeout=aiohttp.ClientTimeout(total=120)
            ) as response:
                data = await response.json()

                if response.status != 200:
                    return TranscriptionResult(
                        id=result_id,
                        provider="whisper",
                        text="",
                        error=data.get("error", {}).get("message", "Unknown error")
                    )

                result = TranscriptionResult(
                    id=result_id,
                    provider="whisper",
                    text=data.get("text", ""),
                    language=data.get("language"),
                    duration_seconds=data.get("duration"),
                    words=data.get("words")
                )
                _transcription_results[result_id] = result
                return result

    except Exception as e:
        return TranscriptionResult(
            id=result_id,
            provider="whisper",
            text="",
            error=str(e)
        )


async def transcribe_assemblyai(
    audio_data: bytes,
    language_code: Optional[str] = None
) -> TranscriptionResult:
    """Transcribe audio using AssemblyAI."""
    result_id = str(uuid.uuid4())

    if not ASSEMBLYAI_API_KEY:
        return TranscriptionResult(
            id=result_id,
            provider="assemblyai",
            text="",
            error="AssemblyAI API key not configured"
        )

    try:
        async with aiohttp.ClientSession() as session:
            # Upload audio file
            async with session.post(
                "https://api.assemblyai.com/v2/upload",
                headers={
                    "authorization": ASSEMBLYAI_API_KEY
                },
                data=audio_data,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as upload_response:
                if upload_response.status != 200:
                    error_text = await upload_response.text()
                    return TranscriptionResult(
                        id=result_id,
                        provider="assemblyai",
                        text="",
                        error=f"Upload failed: {error_text}"
                    )

                upload_data = await upload_response.json()
                audio_url = upload_data.get("upload_url")

            # Create transcription request
            transcript_request = {"audio_url": audio_url}
            if language_code:
                transcript_request["language_code"] = language_code

            async with session.post(
                "https://api.assemblyai.com/v2/transcript",
                headers={
                    "authorization": ASSEMBLYAI_API_KEY,
                    "content-type": "application/json"
                },
                json=transcript_request,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as transcript_response:
                transcript_data = await transcript_response.json()
                transcript_id = transcript_data.get("id")

            # Poll for completion
            max_attempts = 60
            for _ in range(max_attempts):
                async with session.get(
                    f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
                    headers={"authorization": ASSEMBLYAI_API_KEY},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as status_response:
                    status_data = await status_response.json()
                    status = status_data.get("status")

                    if status == "completed":
                        result = TranscriptionResult(
                            id=result_id,
                            provider="assemblyai",
                            text=status_data.get("text", ""),
                            language=status_data.get("language_code"),
                            duration_seconds=status_data.get("audio_duration"),
                            confidence=status_data.get("confidence"),
                            words=status_data.get("words")
                        )
                        _transcription_results[result_id] = result
                        return result

                    elif status == "error":
                        return TranscriptionResult(
                            id=result_id,
                            provider="assemblyai",
                            text="",
                            error=status_data.get("error", "Transcription failed")
                        )

                await asyncio.sleep(2)

            return TranscriptionResult(
                id=result_id,
                provider="assemblyai",
                text="",
                error="Transcription timed out"
            )

    except Exception as e:
        return TranscriptionResult(
            id=result_id,
            provider="assemblyai",
            text="",
            error=str(e)
        )


async def transcribe(
    audio_data: bytes,
    provider: str = "whisper",
    filename: str = "audio.mp3",
    language: Optional[str] = None,
    **kwargs
) -> TranscriptionResult:
    """
    Transcribe audio using the specified provider.

    Args:
        audio_data: Audio file bytes
        provider: STT provider (whisper, assemblyai)
        filename: Original filename for content type detection
        language: Optional language hint
        **kwargs: Additional provider-specific parameters

    Returns:
        TranscriptionResult with transcribed text
    """
    if provider == "whisper":
        return await transcribe_openai(audio_data, filename, language, **kwargs)
    elif provider == "assemblyai":
        return await transcribe_assemblyai(audio_data, language, **kwargs)
    else:
        return await transcribe_openai(audio_data, filename, language, **kwargs)


def get_tts_result(result_id: str) -> Optional[TTSResult]:
    """Get a TTS result by ID."""
    return _tts_results.get(result_id)


def get_transcription_result(result_id: str) -> Optional[TranscriptionResult]:
    """Get a transcription result by ID."""
    return _transcription_results.get(result_id)


def list_tts_results(limit: int = 50) -> List[Dict[str, Any]]:
    """List recent TTS results."""
    results = list(_tts_results.values())
    results.sort(key=lambda x: x.created_at, reverse=True)
    return [
        {
            "id": r.id,
            "text": r.text[:100] + "..." if len(r.text) > 100 else r.text,
            "provider": r.provider,
            "voice": r.voice,
            "has_audio": r.audio_base64 is not None,
            "created_at": r.created_at,
            "error": r.error
        }
        for r in results[:limit]
    ]


def list_transcriptions(limit: int = 50) -> List[Dict[str, Any]]:
    """List recent transcriptions."""
    results = list(_transcription_results.values())
    results.sort(key=lambda x: x.created_at, reverse=True)
    return [
        {
            "id": r.id,
            "text": r.text[:100] + "..." if len(r.text) > 100 else r.text,
            "provider": r.provider,
            "language": r.language,
            "duration_seconds": r.duration_seconds,
            "created_at": r.created_at,
            "error": r.error
        }
        for r in results[:limit]
    ]


def get_available_tts_providers() -> List[Dict[str, Any]]:
    """Get available TTS providers and voices."""
    return [
        {
            "id": "openai",
            "name": "OpenAI TTS",
            "available": bool(OPENAI_API_KEY),
            "voices": [
                {"id": "alloy", "name": "Alloy", "description": "Neutral and balanced"},
                {"id": "echo", "name": "Echo", "description": "Warm and conversational"},
                {"id": "fable", "name": "Fable", "description": "British accent"},
                {"id": "onyx", "name": "Onyx", "description": "Deep and authoritative"},
                {"id": "nova", "name": "Nova", "description": "Friendly and upbeat"},
                {"id": "shimmer", "name": "Shimmer", "description": "Clear and expressive"}
            ],
            "models": ["tts-1", "tts-1-hd"]
        },
        {
            "id": "elevenlabs",
            "name": "ElevenLabs",
            "available": bool(ELEVENLABS_API_KEY),
            "voices": [
                {"id": "21m00Tcm4TlvDq8ikWAM", "name": "Rachel", "description": "American female"},
                {"id": "AZnzlk1XvdvUeBnXmlld", "name": "Domi", "description": "American female"},
                {"id": "EXAVITQu4vr4xnSDxMaL", "name": "Bella", "description": "American female"},
                {"id": "ErXwobaYiN019PkySvjV", "name": "Antoni", "description": "American male"},
                {"id": "VR6AewLTigWG4xSOukaG", "name": "Arnold", "description": "American male"}
            ]
        }
    ]


def get_available_stt_providers() -> List[Dict[str, Any]]:
    """Get available STT providers."""
    return [
        {
            "id": "whisper",
            "name": "OpenAI Whisper",
            "available": bool(OPENAI_API_KEY),
            "languages": "Automatic detection or 50+ languages",
            "features": ["Word-level timestamps", "Language detection"]
        },
        {
            "id": "assemblyai",
            "name": "AssemblyAI",
            "available": bool(ASSEMBLYAI_API_KEY),
            "languages": "Automatic detection or specific languages",
            "features": ["Word-level timestamps", "Speaker diarization", "Sentiment analysis"]
        }
    ]


def tts_result_to_dict(result: TTSResult) -> Dict[str, Any]:
    """Convert TTSResult to dictionary."""
    return {
        "id": result.id,
        "text": result.text,
        "provider": result.provider,
        "voice": result.voice,
        "audio_base64": result.audio_base64,
        "audio_url": result.audio_url,
        "duration_seconds": result.duration_seconds,
        "created_at": result.created_at,
        "error": result.error
    }


def transcription_result_to_dict(result: TranscriptionResult) -> Dict[str, Any]:
    """Convert TranscriptionResult to dictionary."""
    return {
        "id": result.id,
        "provider": result.provider,
        "text": result.text,
        "language": result.language,
        "duration_seconds": result.duration_seconds,
        "confidence": result.confidence,
        "words": result.words,
        "created_at": result.created_at,
        "error": result.error
    }
