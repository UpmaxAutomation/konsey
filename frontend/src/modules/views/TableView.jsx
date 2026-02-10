import { useState, useMemo } from 'react';
import { usePropertyStore } from '../../stores/propertyStore.js';
import './TableView.css';

const FIXED_COLUMNS = [
  { key: 'title', label: 'Title', width: 200 },
  { key: 'card_type', label: 'Type', width: 100 },
  { key: 'created_at', label: 'Created', width: 140 },
];

export default function TableView({
  cards = [],
  propertyDefinitions = [],
  propertyValuesByCard = {},
  onCardSelect,
  onPropertyChange,
  boardId,
}) {
  const { tableSortColumn, tableSortDirection, setTableSort } = usePropertyStore();
  const [resizingCol, setResizingCol] = useState(null);

  // Build column definitions
  const columns = useMemo(() => {
    const propCols = propertyDefinitions.map((def) => ({
      key: `prop_${def.id}`,
      propId: def.id,
      label: def.name,
      width: 150,
      type: def.property_type,
      options: def.options,
    }));
    return [...FIXED_COLUMNS, ...propCols];
  }, [propertyDefinitions]);

  // Sort cards
  const sortedCards = useMemo(() => {
    if (!tableSortColumn) return cards;
    const col = columns.find((c) => c.key === tableSortColumn);
    if (!col) return cards;

    return [...cards].sort((a, b) => {
      let va, vb;
      if (col.propId) {
        va = propertyValuesByCard[a.id]?.[col.propId];
        vb = propertyValuesByCard[b.id]?.[col.propId];
      } else {
        va = a[col.key];
        vb = b[col.key];
      }
      if (va == null && vb == null) return 0;
      if (va == null) return 1;
      if (vb == null) return -1;
      const cmp = String(va).localeCompare(String(vb), undefined, { numeric: true });
      return tableSortDirection === 'desc' ? -cmp : cmp;
    });
  }, [cards, columns, tableSortColumn, tableSortDirection, propertyValuesByCard]);

  const handleSort = (colKey) => {
    if (tableSortColumn === colKey) {
      setTableSort(colKey, tableSortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setTableSort(colKey, 'asc');
    }
  };

  const getCellValue = (card, col) => {
    if (col.propId) {
      return propertyValuesByCard[card.id]?.[col.propId];
    }
    if (col.key === 'created_at') {
      return card.created_at ? new Date(card.created_at).toLocaleDateString() : '';
    }
    return card[col.key] || '';
  };

  const formatCellDisplay = (value, col) => {
    if (value == null || value === '') return '\u2014';
    if (col.type === 'checkbox') return value ? '\u2713' : '\u2717';
    if (col.type === 'multi_select' && Array.isArray(value)) return value.join(', ');
    return String(value);
  };

  return (
    <div className="table-view">
      <div className="table-view__wrapper">
        <table className="table-view__table">
          <thead>
            <tr>
              {columns.map((col) => (
                <th
                  key={col.key}
                  className="table-view__th"
                  style={{ width: col.width }}
                  onClick={() => handleSort(col.key)}
                >
                  <span>{col.label}</span>
                  {tableSortColumn === col.key && (
                    <span className="table-view__sort-icon">
                      {tableSortDirection === 'asc' ? '\u25B2' : '\u25BC'}
                    </span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sortedCards.map((card) => (
              <tr
                key={card.id}
                className="table-view__tr"
                onClick={() => onCardSelect?.(card.id)}
              >
                {columns.map((col) => (
                  <td key={col.key} className="table-view__td">
                    {formatCellDisplay(getCellValue(card, col), col)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        {sortedCards.length === 0 && (
          <div className="table-view__empty">No cards on this board.</div>
        )}
      </div>
    </div>
  );
}
