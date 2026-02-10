import { useCallback } from 'react';
import { useHistoryStore } from '../../../stores/historyStore';

export function useUndoableAction() {
  const pushEntry = useHistoryStore((s) => s.pushEntry);
  const isUndoing = useHistoryStore((s) => s.isUndoing);
  const isRedoing = useHistoryStore((s) => s.isRedoing);

  const recordAction = useCallback((entry) => {
    if (isUndoing || isRedoing) return;
    pushEntry(entry);
  }, [pushEntry, isUndoing, isRedoing]);

  return { recordAction };
}
