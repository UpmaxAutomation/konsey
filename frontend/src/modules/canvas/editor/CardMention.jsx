/**
 * CardMention -- Suggestion popup for [[ card linking.
 * Shows a searchable list of board cards with type icons.
 *
 * @module canvas/editor/CardMention
 */
import { useState, useEffect, useRef, forwardRef, useImperativeHandle } from 'react';
import './CardMention.css';

const TYPE_ICONS = {
  note: '\u270E',
  knowledge: '\u25C8',
  query: '?',
  council_response: '\u25B7',
  council_synthesis: '\u2726',
  file_ref: '\u25A1',
  link: '\u2197',
};

const TYPE_COLORS = {
  note: '#6366f1',
  knowledge: '#8b5cf6',
  query: '#f59e0b',
  council_response: '#06b6d4',
  council_synthesis: '#10b981',
  file_ref: '#64748b',
  link: '#3b82f6',
};

/**
 * Suggestion popup rendered by tippy.js for card mention autocomplete.
 *
 * Keyboard navigation:
 *  - ArrowUp / ArrowDown to move selection
 *  - Enter to confirm
 *
 * @param {Object}   props
 * @param {Array}    props.items   - Filtered card objects
 * @param {Function} props.command - Callback to insert the selected card
 * @param {React.Ref} ref         - Imperative handle for keyboard delegation
 */
const CardMention = forwardRef(({ items, command }, ref) => {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const menuRef = useRef(null);

  // Reset selection when the filtered list changes
  useEffect(() => {
    setSelectedIndex(0);
  }, [items]);

  // Keep the selected item scrolled into view
  useEffect(() => {
    const el = menuRef.current?.querySelector('.card-mention__item--selected');
    if (el) el.scrollIntoView({ block: 'nearest' });
  }, [selectedIndex]);

  useImperativeHandle(ref, () => ({
    onKeyDown({ event }) {
      if (event.key === 'ArrowUp') {
        setSelectedIndex((i) => (i - 1 + items.length) % items.length);
        return true;
      }
      if (event.key === 'ArrowDown') {
        setSelectedIndex((i) => (i + 1) % items.length);
        return true;
      }
      if (event.key === 'Enter') {
        if (items[selectedIndex]) {
          command(items[selectedIndex]);
        }
        return true;
      }
      return false;
    },
  }));

  if (!items.length) {
    return (
      <div className="card-mention" ref={menuRef} role="listbox" aria-label="Card search results">
        <div className="card-mention__empty">No cards found</div>
      </div>
    );
  }

  return (
    <div className="card-mention" ref={menuRef} role="listbox" aria-label="Card search results">
      {items.map((card, index) => {
        const type = card.extra?.is_knowledge ? 'knowledge' : card.card_type;
        const isSelected = index === selectedIndex;
        return (
          <button
            key={card.id}
            type="button"
            role="option"
            aria-selected={isSelected}
            className={`card-mention__item${isSelected ? ' card-mention__item--selected' : ''}`}
            onClick={() => command(card)}
            onMouseEnter={() => setSelectedIndex(index)}
          >
            <span
              className="card-mention__icon"
              style={{ color: TYPE_COLORS[type] || '#6366f1' }}
              aria-hidden="true"
            >
              {TYPE_ICONS[type] || '\u270E'}
            </span>
            <span className="card-mention__title">{card.title || 'Untitled'}</span>
            <span
              className="card-mention__type"
              style={{ color: TYPE_COLORS[type] || '#6366f1' }}
            >
              {type}
            </span>
          </button>
        );
      })}
    </div>
  );
});

CardMention.displayName = 'CardMention';
export default CardMention;
