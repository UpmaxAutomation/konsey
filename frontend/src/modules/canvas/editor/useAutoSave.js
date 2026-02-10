/**
 * useAutoSave -- Debounced autosave hook for card editing.
 * Saves every 2 seconds while content is dirty.
 * Returns save status: 'idle' | 'saving' | 'saved' | 'error'
 */
import { useState, useRef, useEffect, useCallback } from 'react';

const AUTOSAVE_DELAY = 2000;

export default function useAutoSave(saveFn) {
  const [status, setStatus] = useState('idle');
  const timerRef = useRef(null);
  const pendingRef = useRef(null);
  const saveFnRef = useRef(saveFn);
  saveFnRef.current = saveFn;

  const scheduleAutoSave = useCallback((title, content) => {
    pendingRef.current = { title, content };
    setStatus('idle');

    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(async () => {
      const data = pendingRef.current;
      if (!data) return;
      pendingRef.current = null;

      setStatus('saving');
      try {
        await saveFnRef.current(data.title, data.content);
        setStatus('saved');
        // Reset to idle after showing "Saved" for 2s
        setTimeout(() => setStatus((s) => (s === 'saved' ? 'idle' : s)), 2000);
      } catch {
        setStatus('error');
      }
    }, AUTOSAVE_DELAY);
  }, []);

  // Flush pending save immediately (for unmount / explicit save)
  const flush = useCallback(async () => {
    clearTimeout(timerRef.current);
    const data = pendingRef.current;
    if (!data) return;
    pendingRef.current = null;

    setStatus('saving');
    try {
      await saveFnRef.current(data.title, data.content);
      setStatus('saved');
    } catch {
      setStatus('error');
    }
  }, []);

  // Flush pending data and clean up timer on unmount
  useEffect(() => {
    return () => {
      clearTimeout(timerRef.current);
      const data = pendingRef.current;
      if (data) {
        pendingRef.current = null;
        saveFnRef.current(data.title, data.content);
      }
    };
  }, []);

  return { status, scheduleAutoSave, flush };
}
