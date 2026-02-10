import { useMemo } from 'react';
import { usePropertyStore } from '../../stores/propertyStore.js';
import './KanbanView.css';

export default function KanbanView({
  cards = [],
  propertyDefinitions = [],
  propertyValuesByCard = {},
  onCardSelect,
  onPropertyChange,
  boardId,
}) {
  const { kanbanGroupByPropertyId, setKanbanGroupByPropertyId } = usePropertyStore();

  // Only select/multi_select types can be used for grouping
  const groupableProperties = useMemo(
    () => propertyDefinitions.filter((d) => d.property_type === 'select' || d.property_type === 'multi_select'),
    [propertyDefinitions]
  );

  const groupProp = propertyDefinitions.find((d) => d.id === kanbanGroupByPropertyId);

  // Build columns from the grouping property options
  const columns = useMemo(() => {
    if (!groupProp?.options?.choices) return [{ value: '__ungrouped', label: 'All Cards' }];
    const cols = groupProp.options.choices.map((c) => ({
      value: c.value || c,
      label: c.label || c.value || c,
    }));
    cols.push({ value: '__ungrouped', label: 'Ungrouped' });
    return cols;
  }, [groupProp]);

  // Group cards into columns
  const groupedCards = useMemo(() => {
    const groups = {};
    for (const col of columns) {
      groups[col.value] = [];
    }

    for (const card of cards) {
      const propValue = propertyValuesByCard[card.id]?.[kanbanGroupByPropertyId];
      if (!propValue || !groupProp) {
        groups['__ungrouped']?.push(card);
      } else if (groupProp.property_type === 'multi_select' && Array.isArray(propValue)) {
        let placed = false;
        for (const v of propValue) {
          if (groups[v]) {
            groups[v].push(card);
            placed = true;
          }
        }
        if (!placed) groups['__ungrouped']?.push(card);
      } else {
        if (groups[propValue]) {
          groups[propValue].push(card);
        } else {
          groups['__ungrouped']?.push(card);
        }
      }
    }
    return groups;
  }, [cards, columns, propertyValuesByCard, kanbanGroupByPropertyId, groupProp]);

  const handleDrop = (e, columnValue) => {
    e.preventDefault();
    const cardId = e.dataTransfer.getData('text/plain');
    if (!cardId || !kanbanGroupByPropertyId) return;

    const newValue = columnValue === '__ungrouped' ? null : columnValue;
    onPropertyChange?.(cardId, kanbanGroupByPropertyId, newValue);
  };

  const handleDragStart = (e, cardId) => {
    e.dataTransfer.setData('text/plain', cardId);
  };

  return (
    <div className="kanban-view">
      <div className="kanban-view__toolbar">
        <label className="kanban-view__group-label">Group by:</label>
        <select
          className="kanban-view__group-select"
          value={kanbanGroupByPropertyId || ''}
          onChange={(e) => setKanbanGroupByPropertyId(e.target.value || null)}
        >
          <option value="">-- Select property --</option>
          {groupableProperties.map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
      </div>

      <div className="kanban-view__board">
        {columns.map((col) => (
          <div
            key={col.value}
            className="kanban-view__column"
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => handleDrop(e, col.value)}
          >
            <div className="kanban-view__column-header">
              <span className="kanban-view__column-title">{col.label}</span>
              <span className="kanban-view__column-count">{groupedCards[col.value]?.length || 0}</span>
            </div>
            <div className="kanban-view__column-cards">
              {(groupedCards[col.value] || []).map((card) => (
                <div
                  key={card.id}
                  className="kanban-view__card"
                  draggable
                  onDragStart={(e) => handleDragStart(e, card.id)}
                  onClick={() => onCardSelect?.(card.id)}
                >
                  <div className="kanban-view__card-type">{card.card_type}</div>
                  <div className="kanban-view__card-title">{card.title || 'Untitled'}</div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {!kanbanGroupByPropertyId && (
        <div className="kanban-view__hint">
          Select a grouping property above to organize cards into columns.
        </div>
      )}
    </div>
  );
}
