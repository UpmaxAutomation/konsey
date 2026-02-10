import { useState, useEffect, useCallback, useMemo } from 'react';
import { createJournalEntry, listJournalEntries } from '../../../api/boards.js';
import '../styles/JournalPanel.css';

function formatDateLabel(dateStr) {
  if (!dateStr) return '';
  try {
    return new Date(dateStr + 'T00:00:00').toLocaleDateString(undefined, {
      weekday: 'short', month: 'short', day: 'numeric',
    });
  } catch { return dateStr; }
}

function toDateKey(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

function getCalendarDays(year, month) {
  const firstDay = new Date(year, month, 1);
  // Monday = 0, Sunday = 6
  let startOffset = firstDay.getDay() - 1;
  if (startOffset < 0) startOffset = 6;

  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const cells = [];

  // Blank cells before first day
  for (let i = 0; i < startOffset; i++) cells.push(null);
  // Day cells
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);
  // Pad to fill last row
  while (cells.length % 7 !== 0) cells.push(null);

  return cells;
}

export default function JournalPanel({ boardId, onClose, onFocusCard }) {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);

  const today = new Date();
  const [calYear, setCalYear] = useState(today.getFullYear());
  const [calMonth, setCalMonth] = useState(today.getMonth());

  useEffect(() => {
    if (!boardId) return;
    setLoading(true);
    listJournalEntries(boardId)
      .then((data) => setEntries(data.entries || []))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [boardId]);

  // Set of date keys that have entries
  const entryDates = useMemo(() => {
    const set = new Set();
    entries.forEach((e) => { if (e.journal_date) set.add(e.journal_date); });
    return set;
  }, [entries]);

  // Map from date key -> entry id for quick lookup
  const dateToEntry = useMemo(() => {
    const map = {};
    entries.forEach((e) => { if (e.journal_date) map[e.journal_date] = e; });
    return map;
  }, [entries]);

  const calendarCells = useMemo(() => getCalendarDays(calYear, calMonth), [calYear, calMonth]);
  const todayKey = toDateKey(today);
  const monthLabel = new Date(calYear, calMonth).toLocaleDateString(undefined, { month: 'long', year: 'numeric' });

  const handlePrevMonth = () => {
    if (calMonth === 0) { setCalYear((y) => y - 1); setCalMonth(11); }
    else setCalMonth((m) => m - 1);
  };

  const handleNextMonth = () => {
    if (calMonth === 11) { setCalYear((y) => y + 1); setCalMonth(0); }
    else setCalMonth((m) => m + 1);
  };

  const handleDateClick = useCallback(async (day) => {
    if (!day) return;
    const dateKey = `${calYear}-${String(calMonth + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;

    // If entry exists, focus it
    const existing = dateToEntry[dateKey];
    if (existing) {
      onFocusCard?.(existing.id);
      return;
    }

    // Otherwise create new entry
    try {
      const entry = await createJournalEntry(boardId, { date: dateKey, title: `Journal — ${formatDateLabel(dateKey)}` });
      setEntries((prev) => [entry, ...prev]);
      onFocusCard?.(entry.id);
    } catch (err) {
      console.error('Failed to create journal entry:', err);
    }
  }, [boardId, calYear, calMonth, dateToEntry, onFocusCard]);

  const handleCreateToday = useCallback(async () => {
    const dateKey = toDateKey(today);
    const existing = dateToEntry[dateKey];
    if (existing) {
      onFocusCard?.(existing.id);
      return;
    }
    try {
      const entry = await createJournalEntry(boardId, { date: dateKey, title: `Journal — ${formatDateLabel(dateKey)}` });
      setEntries((prev) => [entry, ...prev]);
      onFocusCard?.(entry.id);
    } catch (err) {
      console.error('Failed to create journal entry:', err);
    }
  }, [boardId, onFocusCard, dateToEntry]);

  return (
    <div className="journal-panel">
      <div className="journal-panel__header">
        <h3 className="journal-panel__title">Journal</h3>
        <button className="journal-panel__close" onClick={onClose} aria-label="Close journal">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 6L6 18M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Mini Calendar */}
      <div className="journal-panel__calendar">
        <div className="journal-panel__cal-nav">
          <button className="journal-panel__cal-arrow" onClick={handlePrevMonth} aria-label="Previous month">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M15 18l-6-6 6-6" />
            </svg>
          </button>
          <span className="journal-panel__cal-month">{monthLabel}</span>
          <button className="journal-panel__cal-arrow" onClick={handleNextMonth} aria-label="Next month">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M9 18l6-6-6-6" />
            </svg>
          </button>
        </div>

        <div className="journal-panel__cal-grid">
          {DAY_LABELS.map((d) => (
            <div key={d} className="journal-panel__cal-day-label">{d}</div>
          ))}
          {calendarCells.map((day, i) => {
            if (day === null) return <div key={`blank-${i}`} className="journal-panel__cal-cell" />;
            const dateKey = `${calYear}-${String(calMonth + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
            const hasEntry = entryDates.has(dateKey);
            const isToday = dateKey === todayKey;
            return (
              <button
                key={dateKey}
                className={`journal-panel__cal-cell journal-panel__cal-cell--day${isToday ? ' journal-panel__cal-cell--today' : ''}${hasEntry ? ' journal-panel__cal-cell--has-entry' : ''}`}
                onClick={() => handleDateClick(day)}
              >
                {day}
                {hasEntry && <span className="journal-panel__cal-dot" />}
              </button>
            );
          })}
        </div>
      </div>

      <button className="journal-panel__today-btn" onClick={handleCreateToday}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 5v14M5 12h14" />
        </svg>
        Today's Entry
      </button>

      <div className="journal-panel__list">
        {loading && <div className="journal-panel__loading">Loading...</div>}
        {!loading && entries.length === 0 && (
          <div className="journal-panel__empty">No journal entries yet. Create today's entry to get started.</div>
        )}
        {entries.map((entry) => (
          <button
            key={entry.id}
            className="journal-panel__entry"
            onClick={() => onFocusCard?.(entry.id)}
          >
            <span className="journal-panel__entry-date">{formatDateLabel(entry.journal_date)}</span>
            <span className="journal-panel__entry-title">{entry.title || 'Untitled'}</span>
            <span className="journal-panel__entry-preview">
              {entry.content?.slice(0, 80) || 'Empty entry'}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
