import { memo } from 'react';
import '../styles/TabBar.css';

const TYPE_LABELS = {
  note: 'Note',
  knowledge: 'Knowledge',
  query: 'Query',
  council_response: 'Response',
  council_synthesis: 'Synthesis',
  file_ref: 'File',
  link: 'Link',
  board_ref: 'Board',
  workflow_output: 'Workflow',
  linked_card: 'Linked',
};

function truncate(str, max = 20) {
  if (!str) return 'Untitled';
  return str.length > max ? str.slice(0, max) + '\u2026' : str;
}

function TabBar({ tabs, activeTabId, onTabSelect, onTabClose }) {
  if (!tabs || tabs.length === 0) return null;

  return (
    <div className="tab-bar">
      {tabs.map((tab) => (
        <div
          key={tab.id}
          className={`tab-bar__tab${tab.id === activeTabId ? ' tab-bar__tab--active' : ''}`}
          onClick={() => onTabSelect?.(tab.cardId)}
          title={tab.title || 'Untitled'}
        >
          {tab.cardType && (
            <span className="tab-bar__type-badge">{TYPE_LABELS[tab.cardType] || tab.cardType}</span>
          )}
          <span className="tab-bar__title">{truncate(tab.title)}</span>
          <button
            className="tab-bar__close"
            onClick={(e) => {
              e.stopPropagation();
              onTabClose?.(tab.id);
            }}
            aria-label={`Close tab ${tab.title || 'Untitled'}`}
          >
            &times;
          </button>
        </div>
      ))}
    </div>
  );
}

export default memo(TabBar);
