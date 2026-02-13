import { useState, useMemo, useCallback, useRef } from 'react';
import './TimelineView.css';

const DAY_MS = 86400000;
const ZOOM_LEVELS = { month: 4, week: 16, day: 40 };

const TYPE_COLORS = {
  note: '#6366f1',
  knowledge: '#8b5cf6',
  query: '#f59e0b',
  council_response: '#06b6d4',
  council_synthesis: '#10b981',
  link: '#3b82f6',
  default: '#94a3b8',
};

export default function TimelineView({
  cards,
  propertyDefinitions,
  propertyValuesByCard,
  onCardSelect,
  onPropertyChange,
  boardId,
}) {
  const [zoom, setZoom] = useState('week');
  const containerRef = useRef(null);
  const pxPerDay = ZOOM_LEVELS[zoom];

  const dateProps = useMemo(
    () => propertyDefinitions.filter((p) => p.property_type === 'date'),
    [propertyDefinitions],
  );

  const { scheduled, unscheduled, minDate, maxDate } = useMemo(() => {
    const scheduled = [];
    const unscheduled = [];
    let min = Infinity;
    let max = -Infinity;

    for (const card of cards) {
      const vals = propertyValuesByCard[card.id] || {};
      let startDate = null;
      let endDate = null;

      for (const dp of dateProps) {
        const v = vals[dp.id];
        if (!v) continue;
        const d = new Date(v).getTime();
        if (!startDate || d < startDate) startDate = d;
        if (!endDate || d > endDate) endDate = d;
      }

      if (startDate) {
        if (!endDate || endDate === startDate) endDate = startDate + DAY_MS * 3;
        scheduled.push({ ...card, startDate, endDate });
        if (startDate < min) min = startDate;
        if (endDate > max) max = endDate;
      } else {
        unscheduled.push(card);
      }
    }

    const today = Date.now();
    if (min === Infinity) {
      min = today - 30 * DAY_MS;
      max = today + 30 * DAY_MS;
    }
    min = min - 7 * DAY_MS;
    max = max + 7 * DAY_MS;

    return { scheduled, unscheduled, minDate: min, maxDate: max };
  }, [cards, propertyValuesByCard, dateProps]);

  const totalDays = Math.ceil((maxDate - minDate) / DAY_MS);
  const totalWidth = totalDays * pxPerDay;
  const rowHeight = 36;
  const headerHeight = 40;
  const todayOffset = ((Date.now() - minDate) / DAY_MS) * pxPerDay;

  const dateLabels = useMemo(() => {
    const labels = [];
    const d = new Date(minDate);
    const step = zoom === 'month' ? 7 : 1;
    while (d.getTime() <= maxDate) {
      labels.push({
        x: ((d.getTime() - minDate) / DAY_MS) * pxPerDay,
        label: d.toLocaleDateString(undefined, zoom === 'month'
          ? { month: 'short', day: 'numeric' }
          : { weekday: 'short', day: 'numeric' }),
        isMonthStart: d.getDate() === 1,
      });
      d.setDate(d.getDate() + step);
    }
    return labels;
  }, [minDate, maxDate, pxPerDay, zoom]);

  const handleBarClick = useCallback(
    (cardId) => {
      onCardSelect?.(cardId);
    },
    [onCardSelect],
  );

  const svgHeight = headerHeight + (scheduled.length + unscheduled.length + 2) * rowHeight;

  return (
    <div className="timeline-view">
      <div className="timeline-view__controls">
        <span className="timeline-view__title">Timeline</span>
        <div className="timeline-view__zoom" role="group" aria-label="Zoom level">
          {Object.keys(ZOOM_LEVELS).map((z) => (
            <button
              key={z}
              className={`timeline-view__zoom-btn${zoom === z ? ' timeline-view__zoom-btn--active' : ''}`}
              onClick={() => setZoom(z)}
              aria-pressed={zoom === z}
            >
              {z.charAt(0).toUpperCase() + z.slice(1)}
            </button>
          ))}
        </div>
        <span className="timeline-view__count">
          {scheduled.length} scheduled, {unscheduled.length} unscheduled
        </span>
      </div>

      <div className="timeline-view__scroll" ref={containerRef}>
        <svg
          width={totalWidth}
          height={svgHeight}
          role="img"
          aria-label="Timeline chart"
        >
          {/* Header */}
          <g className="timeline-view__header">
            <rect x={0} y={0} width={totalWidth} height={headerHeight} fill="var(--bg-secondary, #f8fafc)" />
            {dateLabels.map((dl, i) => (
              <g key={i}>
                <line x1={dl.x} y1={headerHeight - 4} x2={dl.x} y2={headerHeight} stroke="var(--border-primary, #e2e8f0)" />
                <text x={dl.x + 4} y={headerHeight - 10} fontSize={11} fill="var(--text-muted, #94a3b8)">
                  {dl.label}
                </text>
              </g>
            ))}
            <line x1={0} y1={headerHeight} x2={totalWidth} y2={headerHeight} stroke="var(--border-primary, #e2e8f0)" />
          </g>

          {/* Today line */}
          {todayOffset > 0 && todayOffset < totalWidth && (
            <line
              x1={todayOffset}
              y1={0}
              x2={todayOffset}
              y2={svgHeight}
              stroke="#ef4444"
              strokeWidth={2}
              strokeDasharray="4,2"
            />
          )}

          {/* Scheduled bars */}
          {scheduled.map((card, i) => {
            const x = ((card.startDate - minDate) / DAY_MS) * pxPerDay;
            const w = Math.max(((card.endDate - card.startDate) / DAY_MS) * pxPerDay, pxPerDay);
            const y = headerHeight + i * rowHeight + 4;
            const color = TYPE_COLORS[card.card_type] || TYPE_COLORS.default;
            return (
              <g key={card.id} onClick={() => handleBarClick(card.id)} style={{ cursor: 'pointer' }}>
                <rect x={x} y={y} width={w} height={rowHeight - 8} rx={4} fill={color} opacity={0.85} />
                <text x={x + 6} y={y + rowHeight / 2} fontSize={12} fill="#fff" dominantBaseline="central">
                  {(card.title || 'Untitled').slice(0, Math.floor(w / 7))}
                </text>
              </g>
            );
          })}

          {/* Unscheduled section */}
          {unscheduled.length > 0 && (
            <>
              <text
                x={8}
                y={headerHeight + scheduled.length * rowHeight + rowHeight - 6}
                fontSize={12}
                fill="var(--text-muted)"
                fontWeight={600}
              >
                Unscheduled ({unscheduled.length})
              </text>
              {unscheduled.map((card, i) => {
                const y = headerHeight + (scheduled.length + 1 + i) * rowHeight + 4;
                const color = TYPE_COLORS[card.card_type] || TYPE_COLORS.default;
                return (
                  <g key={card.id} onClick={() => handleBarClick(card.id)} style={{ cursor: 'pointer' }}>
                    <rect x={8} y={y} width={120} height={rowHeight - 8} rx={4} fill={color} opacity={0.4} />
                    <text x={14} y={y + rowHeight / 2} fontSize={12} fill="var(--text-primary)" dominantBaseline="central">
                      {(card.title || 'Untitled').slice(0, 16)}
                    </text>
                  </g>
                );
              })}
            </>
          )}
        </svg>
      </div>
    </div>
  );
}
