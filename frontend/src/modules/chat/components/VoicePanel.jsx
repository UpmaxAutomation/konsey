/**
 * VoicePanel - Voice TTS & Transcription Interface.
 *
 * Features:
 * - Text-to-Speech with multiple voices
 * - Speech-to-Text transcription
 * - Audio playback
 * - Recording support
 */

import React, { useState, useEffect, useRef } from 'react';
import { api } from '../../../api';
import '../styles/VoicePanel.css';

export default function VoicePanel({ onClose }) {
  const [activeTab, setActiveTab] = useState('tts');

  // TTS State
  const [ttsText, setTtsText] = useState('');
  const [ttsProvider, setTtsProvider] = useState('openai');
  const [ttsVoice, setTtsVoice] = useState('alloy');
  const [ttsSpeed, setTtsSpeed] = useState(1.0);
  const [isGeneratingAudio, setIsGeneratingAudio] = useState(false);
  const [currentAudio, setCurrentAudio] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);

  // STT State
  const [sttProvider, setSttProvider] = useState('whisper');
  const [sttLanguage, setSttLanguage] = useState('');
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [transcription, setTranscription] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [recordedBlob, setRecordedBlob] = useState(null);

  // Providers
  const [ttsProviders, setTtsProviders] = useState([]);
  const [sttProviders, setSttProviders] = useState([]);

  const [error, setError] = useState(null);
  const audioRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);

  // Load providers
  useEffect(() => {
    const loadProviders = async () => {
      try {
        const [tts, stt] = await Promise.all([
          api.getTTSProviders(),
          api.getSTTProviders()
        ]);
        setTtsProviders(tts.providers || []);
        setSttProviders(stt.providers || []);
      } catch (err) {
        console.error('Failed to load providers:', err);
      }
    };
    loadProviders();
  }, []);

  // Audio playback
  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.onended = () => setIsPlaying(false);
    }
  }, [currentAudio]);

  const handleGenerateTTS = async () => {
    if (!ttsText.trim() || isGeneratingAudio) return;

    setError(null);
    setIsGeneratingAudio(true);

    try {
      const result = await api.textToSpeech({
        text: ttsText.trim(),
        provider: ttsProvider,
        voice: ttsVoice,
        speed: ttsSpeed,
      });

      if (result.audio_base64) {
        setCurrentAudio(result);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setIsGeneratingAudio(false);
    }
  };

  const handlePlayPause = () => {
    if (!audioRef.current) return;

    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      audioRef.current.play();
      setIsPlaying(true);
    }
  };

  const handleDownloadAudio = () => {
    if (!currentAudio?.audio_base64) return;

    const link = document.createElement('a');
    link.href = `data:audio/mp3;base64,${currentAudio.audio_base64}`;
    link.download = `speech-${currentAudio.id}.mp3`;
    link.click();
  };

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setRecordedBlob(null);
    }
  };

  const handleStartRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream);
      chunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (e) => {
        chunksRef.current.push(e.data);
      };

      mediaRecorderRef.current.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        setRecordedBlob(blob);
        setSelectedFile(null);
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorderRef.current.start();
      setIsRecording(true);
    } catch (err) {
      setError('Microphone access denied');
    }
  };

  const handleStopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const handleTranscribe = async () => {
    const fileToTranscribe = selectedFile || (recordedBlob ? new File([recordedBlob], 'recording.webm') : null);
    if (!fileToTranscribe || isTranscribing) return;

    setError(null);
    setIsTranscribing(true);

    try {
      const result = await api.transcribeAudio(
        fileToTranscribe,
        sttProvider,
        sttLanguage || null
      );
      setTranscription(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsTranscribing(false);
    }
  };

  const selectedTtsProvider = ttsProviders.find(p => p.id === ttsProvider);
  const voices = selectedTtsProvider?.voices || [];

  return (
    <div className="voice-panel">
      <div className="vp-header">
        <h2>
          <span className="vp-icon">🎙️</span>
          Voice Studio
        </h2>
        <p className="vp-description">
          Text-to-Speech and Speech-to-Text powered by AI.
        </p>
        {onClose && (
          <button className="close-btn" onClick={onClose}>×</button>
        )}
      </div>

      <div className="vp-tabs">
        <button
          className={`vp-tab ${activeTab === 'tts' ? 'active' : ''}`}
          onClick={() => setActiveTab('tts')}
        >
          🔊 Text to Speech
        </button>
        <button
          className={`vp-tab ${activeTab === 'stt' ? 'active' : ''}`}
          onClick={() => setActiveTab('stt')}
        >
          📝 Speech to Text
        </button>
      </div>

      <div className="vp-content">
        {error && (
          <div className="vp-error">
            <strong>Error:</strong> {error}
            <button onClick={() => setError(null)}>×</button>
          </div>
        )}

        {/* TTS Tab */}
        {activeTab === 'tts' && (
          <div className="vp-tts">
            <div className="vp-form-group">
              <label>Text to speak</label>
              <textarea
                value={ttsText}
                onChange={(e) => setTtsText(e.target.value)}
                placeholder="Enter the text you want to convert to speech..."
                rows={4}
                disabled={isGeneratingAudio}
              />
            </div>

            <div className="vp-options-row">
              <div className="vp-option">
                <label>Provider</label>
                <select
                  value={ttsProvider}
                  onChange={(e) => {
                    setTtsProvider(e.target.value);
                    setTtsVoice(ttsProviders.find(p => p.id === e.target.value)?.voices?.[0]?.id || '');
                  }}
                  disabled={isGeneratingAudio}
                >
                  {ttsProviders.map(p => (
                    <option key={p.id} value={p.id} disabled={!p.available}>
                      {p.name} {!p.available && '(Not configured)'}
                    </option>
                  ))}
                </select>
              </div>

              <div className="vp-option">
                <label>Voice</label>
                <select
                  value={ttsVoice}
                  onChange={(e) => setTtsVoice(e.target.value)}
                  disabled={isGeneratingAudio}
                >
                  {voices.map(v => (
                    <option key={v.id} value={v.id}>
                      {v.name} - {v.description}
                    </option>
                  ))}
                </select>
              </div>

              <div className="vp-option">
                <label>Speed: {ttsSpeed}x</label>
                <input
                  type="range"
                  min="0.25"
                  max="4"
                  step="0.25"
                  value={ttsSpeed}
                  onChange={(e) => setTtsSpeed(parseFloat(e.target.value))}
                  disabled={isGeneratingAudio}
                />
              </div>
            </div>

            <button
              className="vp-generate-btn"
              onClick={handleGenerateTTS}
              disabled={!ttsText.trim() || isGeneratingAudio}
            >
              {isGeneratingAudio ? (
                <>
                  <span className="spinner"></span>
                  Generating...
                </>
              ) : (
                <>
                  <span>🔊</span>
                  Generate Speech
                </>
              )}
            </button>

            {currentAudio && (
              <div className="vp-audio-player">
                <audio
                  ref={audioRef}
                  src={`data:audio/mp3;base64,${currentAudio.audio_base64}`}
                />
                <div className="vp-player-controls">
                  <button className="vp-play-btn" onClick={handlePlayPause}>
                    {isPlaying ? '⏸️' : '▶️'}
                  </button>
                  <div className="vp-audio-info">
                    <span className="vp-voice-label">{currentAudio.voice}</span>
                    <span className="vp-text-preview">
                      {currentAudio.text.slice(0, 50)}...
                    </span>
                  </div>
                  <button className="vp-download-btn" onClick={handleDownloadAudio}>
                    ⬇️ Download
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* STT Tab */}
        {activeTab === 'stt' && (
          <div className="vp-stt">
            <div className="vp-options-row">
              <div className="vp-option">
                <label>Provider</label>
                <select
                  value={sttProvider}
                  onChange={(e) => setSttProvider(e.target.value)}
                  disabled={isTranscribing}
                >
                  {sttProviders.map(p => (
                    <option key={p.id} value={p.id} disabled={!p.available}>
                      {p.name} {!p.available && '(Not configured)'}
                    </option>
                  ))}
                </select>
              </div>

              <div className="vp-option">
                <label>Language (optional)</label>
                <input
                  type="text"
                  value={sttLanguage}
                  onChange={(e) => setSttLanguage(e.target.value)}
                  placeholder="e.g., en, es, fr"
                  disabled={isTranscribing}
                />
              </div>
            </div>

            <div className="vp-audio-input">
              <div className="vp-record-section">
                <button
                  className={`vp-record-btn ${isRecording ? 'recording' : ''}`}
                  onClick={isRecording ? handleStopRecording : handleStartRecording}
                >
                  {isRecording ? '⏹️ Stop Recording' : '🎤 Record Audio'}
                </button>
                {recordedBlob && (
                  <span className="vp-recorded-label">✓ Recording ready</span>
                )}
              </div>

              <div className="vp-or-divider">
                <span>or</span>
              </div>

              <div className="vp-file-section">
                <input
                  type="file"
                  accept="audio/*"
                  onChange={handleFileSelect}
                  disabled={isTranscribing}
                  id="audio-file-input"
                />
                <label htmlFor="audio-file-input" className="vp-file-label">
                  📁 Choose File
                </label>
                {selectedFile && (
                  <span className="vp-file-name">{selectedFile.name}</span>
                )}
              </div>
            </div>

            <button
              className="vp-transcribe-btn"
              onClick={handleTranscribe}
              disabled={(!selectedFile && !recordedBlob) || isTranscribing}
            >
              {isTranscribing ? (
                <>
                  <span className="spinner"></span>
                  Transcribing...
                </>
              ) : (
                <>
                  <span>📝</span>
                  Transcribe
                </>
              )}
            </button>

            {transcription && (
              <div className="vp-transcription-result">
                <h4>Transcription</h4>
                <div className="vp-transcription-text">
                  {transcription.text}
                </div>
                {transcription.language && (
                  <div className="vp-transcription-meta">
                    <span>Language: {transcription.language}</span>
                    {transcription.duration_seconds && (
                      <span>Duration: {transcription.duration_seconds.toFixed(1)}s</span>
                    )}
                    {transcription.confidence && (
                      <span>Confidence: {(transcription.confidence * 100).toFixed(1)}%</span>
                    )}
                  </div>
                )}
                <button
                  className="vp-copy-btn"
                  onClick={() => navigator.clipboard.writeText(transcription.text)}
                >
                  📋 Copy Text
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
