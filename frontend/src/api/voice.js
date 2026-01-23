/**
 * Voice API - Text-to-Speech (TTS) and Speech-to-Text (STT).
 */

import { API_BASE, authFetch } from './client.js';

/**
 * Convert text to speech.
 * @param {Object} params - TTS parameters
 * @param {string} params.text - Text to convert
 * @param {string} params.provider - Provider (openai, elevenlabs)
 * @param {string} params.voice - Voice ID
 * @param {string} params.model - Model (tts-1, tts-1-hd)
 * @param {number} params.speed - Speed (0.25 - 4.0)
 * @returns {Promise<Object>} Audio data in base64
 */
export async function textToSpeech({ text, provider = 'openai', voice = 'alloy', model = 'tts-1', speed = 1.0 }) {
  const response = await authFetch(`${API_BASE}/api/voice/tts`, {
    method: 'POST',
    body: JSON.stringify({ text, provider, voice, model, speed }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to generate speech');
  }
  return response.json();
}

/**
 * Transcribe audio to text.
 * @param {File} file - Audio file
 * @param {string} provider - Provider (whisper, assemblyai)
 * @param {string} language - Language code (optional)
 * @returns {Promise<Object>} Transcription result
 */
export async function transcribeAudio(file, provider = 'whisper', language = null) {
  const formData = new FormData();
  formData.append('file', file);

  const token = localStorage.getItem('access_token');
  const headers = token ? { 'Authorization': `Bearer ${token}` } : {};

  let url = `${API_BASE}/api/voice/transcribe?provider=${provider}`;
  if (language) {
    url += `&language=${language}`;
  }

  const response = await fetch(url, {
    method: 'POST',
    headers,
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to transcribe audio');
  }
  return response.json();
}

/**
 * Get available TTS providers and voices.
 * @returns {Promise<Object>} List of providers
 */
export async function getTTSProviders() {
  const response = await fetch(`${API_BASE}/api/voice/tts/providers`);
  if (!response.ok) {
    throw new Error('Failed to get TTS providers');
  }
  return response.json();
}

/**
 * Get available STT providers.
 * @returns {Promise<Object>} List of providers
 */
export async function getSTTProviders() {
  const response = await fetch(`${API_BASE}/api/voice/stt/providers`);
  if (!response.ok) {
    throw new Error('Failed to get STT providers');
  }
  return response.json();
}

/**
 * List TTS history.
 * @param {number} limit - Maximum results
 * @returns {Promise<Object>} List of TTS results
 */
export async function listTTSHistory(limit = 50) {
  const response = await authFetch(`${API_BASE}/api/voice/tts?limit=${limit}`);
  if (!response.ok) {
    throw new Error('Failed to list TTS history');
  }
  return response.json();
}

/**
 * List transcription history.
 * @param {number} limit - Maximum results
 * @returns {Promise<Object>} List of transcriptions
 */
export async function listTranscriptions(limit = 50) {
  const response = await authFetch(`${API_BASE}/api/voice/transcriptions?limit=${limit}`);
  if (!response.ok) {
    throw new Error('Failed to list transcriptions');
  }
  return response.json();
}
