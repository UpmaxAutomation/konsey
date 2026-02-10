/**
 * SlashMenu -- Dropdown command menu triggered by typing "/" in the editor.
 *
 * Rendered as a suggestion popup via @tiptap/suggestion.
 * Arrow keys navigate, Enter selects, Escape closes.
 *
 * @module canvas/editor/SlashMenu
 */
import { useState, useEffect, useRef, forwardRef, useImperativeHandle } from 'react';
import { filterCommands, groupByCategory } from './slash-commands';
import './SlashMenu.css';

const SlashMenu = forwardRef(({ query, command, editor }, ref) => {
  const filtered = filterCommands(query);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const menuRef = useRef(null);

  // Reset selection when query changes
  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  // Scroll selected item into view
  useEffect(() => {
    const el = menuRef.current?.querySelector('.slash-menu__item--selected');
    if (el) el.scrollIntoView({ block: 'nearest' });
  }, [selectedIndex]);

  useImperativeHandle(ref, () => ({
    onKeyDown({ event }) {
      if (event.key === 'ArrowUp') {
        setSelectedIndex((i) => (i - 1 + filtered.length) % filtered.length);
        return true;
      }
      if (event.key === 'ArrowDown') {
        setSelectedIndex((i) => (i + 1) % filtered.length);
        return true;
      }
      if (event.key === 'Enter') {
        if (filtered[selectedIndex]) {
          filtered[selectedIndex].command(editor);
          command({});
        }
        return true;
      }
      return false;
    },
  }));

  if (filtered.length === 0) {
    return (
      <div className="slash-menu" ref={menuRef} role="listbox" aria-label="Slash commands">
        <div className="slash-menu__empty">No commands found</div>
      </div>
    );
  }

  const groups = groupByCategory(filtered);
  let flatIndex = 0;

  return (
    <div className="slash-menu" ref={menuRef} role="listbox" aria-label="Slash commands">
      {Object.entries(groups).map(([category, cmds]) => (
        <div key={category} className="slash-menu__group" role="group" aria-label={category}>
          <div className="slash-menu__group-label" aria-hidden="true">{category}</div>
          {cmds.map((cmd) => {
            const idx = flatIndex++;
            const isSelected = idx === selectedIndex;
            return (
              <button
                key={cmd.title}
                type="button"
                role="option"
                aria-selected={isSelected}
                className={`slash-menu__item${isSelected ? ' slash-menu__item--selected' : ''}`}
                onClick={() => {
                  cmd.command(editor);
                  command({});
                }}
                onMouseEnter={() => setSelectedIndex(idx)}
              >
                <span className="slash-menu__icon" aria-hidden="true">{cmd.icon}</span>
                <span className="slash-menu__text">
                  <span className="slash-menu__title">{cmd.title}</span>
                  <span className="slash-menu__desc">{cmd.description}</span>
                </span>
              </button>
            );
          })}
        </div>
      ))}
    </div>
  );
});

SlashMenu.displayName = 'SlashMenu';
export default SlashMenu;
