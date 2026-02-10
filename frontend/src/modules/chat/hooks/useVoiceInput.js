import { useState, useEffect, useRef } from 'react';

/**
 * Hook for speech recognition / voice input functionality.
 * Manages microphone access, interim transcripts, and auto-restart on silence.
 *
 * @param {Object} params
 * @param {Function} params.setInput - Setter for the text input state
 * @param {Object} params.toast - Toast notification instance
 * @param {React.RefObject} params.textareaRef - Ref to the textarea element
 * @returns {Object} Voice input state and controls
 */
export function useVoiceInput({ setInput, toast, textareaRef }) {
  const [isListening, setIsListening] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(false);
  const [interimTranscript, setInterimTranscript] = useState('');
  const recognitionRef = useRef(null);

  // Check for speech recognition support
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const isSecureContext = window.isSecureContext ||
      window.location.hostname === 'localhost' ||
      window.location.hostname === '127.0.0.1';

    if (SpeechRecognition && isSecureContext) {
      setSpeechSupported(true);
    }
    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (e) {
          // Ignore errors on cleanup
        }
        recognitionRef.current = null;
      }
    };
  }, []);

  // Create/manage recognition instance when listening state changes
  useEffect(() => {
    if (!isListening) {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (e) {
          // Ignore - might already be stopped
        }
      }
      setInterimTranscript('');
      return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = navigator.language || 'en-US';

    recognition.onresult = (event) => {
      let finalTranscript = '';
      let interim = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcript;
        } else {
          interim += transcript;
        }
      }

      setInterimTranscript(interim);

      if (finalTranscript) {
        setInput(prev => prev + finalTranscript + ' ');
        setInterimTranscript('');
      }
    };

    recognition.onerror = (event) => {
      console.error('Speech recognition error:', event.error);
      const fatalErrors = ['not-allowed', 'audio-capture', 'service-not-allowed', 'network'];
      if (fatalErrors.includes(event.error)) {
        setIsListening(false);
        setInterimTranscript('');
      }
      switch (event.error) {
        case 'no-speech':
          break;
        case 'audio-capture':
          toast.error('No microphone found. Please connect a microphone.');
          break;
        case 'not-allowed':
        case 'service-not-allowed':
          toast.error('Microphone access denied. Please allow microphone in browser settings.');
          break;
        case 'network':
          toast.error('Cannot connect to speech service. Check internet, VPN, or try disabling ad blockers.');
          break;
        case 'aborted':
          break;
        default:
          console.warn('Speech recognition issue:', event.error);
      }
    };

    recognition.onend = () => {
      if (isListening && recognitionRef.current === recognition) {
        try {
          recognition.start();
        } catch (e) {
          console.warn('Failed to restart recognition:', e);
          setIsListening(false);
          setInterimTranscript('');
        }
      }
    };

    recognitionRef.current = recognition;

    const startTimeout = setTimeout(() => {
      try {
        recognition.start();
      } catch (e) {
        console.error('Failed to start recognition:', e);
        setIsListening(false);
        if (e.message?.includes('already started')) {
          // Recognition was already started, ignore
        } else {
          toast.error('Failed to start voice input. Please try again.');
        }
      }
    }, 100);

    return () => {
      clearTimeout(startTimeout);
      if (recognitionRef.current === recognition) {
        try {
          recognition.stop();
        } catch (e) {
          // Ignore
        }
      }
    };
  }, [isListening, toast]);

  const toggleListening = async () => {
    if (!speechSupported) {
      toast.error('Speech recognition not available in this browser. Try Chrome or Edge.');
      return;
    }

    if (isListening) {
      setIsListening(false);
    } else {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        stream.getTracks().forEach(track => track.stop());

        if (!navigator.onLine) {
          toast.error('Speech recognition requires internet connection.');
          return;
        }

        setIsListening(true);
        textareaRef.current?.focus();
      } catch (err) {
        console.error('Microphone permission error:', err);
        if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
          toast.error('Microphone access denied. Please allow microphone in browser settings.');
        } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
          toast.error('No microphone found. Please connect a microphone.');
        } else if (err.name === 'NotReadableError' || err.name === 'TrackStartError') {
          toast.error('Microphone is in use by another application.');
        } else {
          toast.error('Could not access microphone: ' + err.message);
        }
      }
    }
  };

  return {
    isListening,
    speechSupported,
    interimTranscript,
    toggleListening,
  };
}

export default useVoiceInput;
