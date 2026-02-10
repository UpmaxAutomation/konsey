import { useState, useCallback } from 'react';

/**
 * SynthesisExpander -- drill-down into Stage 1/2/3 data inside a council
 * synthesis card. Renders collapsible sections for individual responses and
 * peer rankings. Stage 3 is a simple label since the card body already shows
 * the synthesised answer.
 *
 * @param {{ extra: { stage1, stage2, metadata, model } }} props
 */

const ACCENT_COLORS = [
  '#6366f1', '#06b6d4', '#f59e0b', '#10b981',
  '#8b5cf6', '#ec4899', '#3b82f6', '#ef4444',
];

function modelShort(name) {
  if (!name) return '?';
  return name.split('/').pop();
}

function truncate(text, len = 200) {
  if (!text) return '';
  return text.length > len ? text.slice(0, len) + '...' : text;
}

function Section({ label, count, children }) {
  const [open, setOpen] = useState(false);
  const toggle = useCallback((e) => {
    e.stopPropagation();
    setOpen((v) => !v);
  }, []);

  return (
    <div className="synthesis-expander__section">
      <button
        className="synthesis-expander__header nodrag"
        onClick={toggle}
        aria-expanded={open}
      >
        <svg
          className={`synthesis-expander__chevron${open ? ' synthesis-expander__chevron--open' : ''}`}
          width="8" height="8" viewBox="0 0 24 24"
          fill="none" stroke="currentColor" strokeWidth="2.5"
        >
          <path d="M9 18l6-6-6-6" />
        </svg>
        <span>{label}</span>
        {count != null && (
          <span className="synthesis-expander__count">{count}</span>
        )}
      </button>
      {open && (
        <div className="synthesis-expander__body nodrag nowheel">
          {children}
        </div>
      )}
    </div>
  );
}

function SynthesisExpander({ extra }) {
  const { stage1, stage2, metadata } = extra || {};
  const [expandedIdx, setExpandedIdx] = useState(null);
  const rankings = metadata?.aggregate_rankings;
  const sortedRankings = rankings
    ? Object.entries(rankings).sort((a, b) => a[1].avg_rank - b[1].avg_rank)
    : null;

  if (!stage1 || stage1.length === 0) return null;

  return (
    <div className="synthesis-expander">
      {/* Stage 1 */}
      <Section label="Stage 1: Individual Responses" count={`${stage1.length} models`}>
        {stage1.map((item, i) => (
          <div key={i} className="synthesis-expander__response">
            <div className="synthesis-expander__response-header">
              <span
                className="synthesis-expander__pill"
                style={{ background: ACCENT_COLORS[i % ACCENT_COLORS.length] }}
              >
                {modelShort(item.model)}
              </span>
              {item.response && item.response.length > 200 && (
                <button
                  className="synthesis-expander__expand-btn nodrag"
                  onClick={(e) => {
                    e.stopPropagation();
                    setExpandedIdx(expandedIdx === i ? null : i);
                  }}
                >
                  {expandedIdx === i ? 'less' : 'more'}
                </button>
              )}
            </div>
            <div className="synthesis-expander__response-text">
              {expandedIdx === i ? item.response : truncate(item.response)}
            </div>
          </div>
        ))}
      </Section>

      {/* Stage 2 */}
      {stage2 && stage2.length > 0 && (
        <Section label="Stage 2: Rankings">
          {sortedRankings ? (
            <div className="synthesis-expander__rankings">
              {sortedRankings.map(([label, info], i) => {
                const model = metadata?.label_to_model?.[label];
                const pct = Math.max(0, 100 - ((info.avg_rank - 1) / Math.max(1, sortedRankings.length - 1)) * 100);
                return (
                  <div key={label} className="synthesis-expander__rank-row">
                    <span className="synthesis-expander__rank-pos">#{i + 1}</span>
                    <span
                      className="synthesis-expander__pill"
                      style={{ background: ACCENT_COLORS[i % ACCENT_COLORS.length] }}
                    >
                      {modelShort(model || label)}
                    </span>
                    <div className="synthesis-expander__rank-bar-track">
                      <div
                        className="synthesis-expander__rank-bar-fill"
                        style={{ width: `${pct}%`, background: ACCENT_COLORS[i % ACCENT_COLORS.length] }}
                      />
                    </div>
                    <span className="synthesis-expander__rank-avg">
                      {info.avg_rank.toFixed(1)}
                    </span>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="synthesis-expander__no-data">No aggregate rankings available</div>
          )}
        </Section>
      )}

      {/* Stage 3 label */}
      <div className="synthesis-expander__stage3-label">
        Stage 3: Final Synthesis
        {extra.model && (
          <span className="synthesis-expander__pill synthesis-expander__pill--chairman">
            {modelShort(extra.model)}
          </span>
        )}
      </div>
    </div>
  );
}

export default SynthesisExpander;
