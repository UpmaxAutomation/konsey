import { useState, useMemo } from 'react';
import {
  usePropertyDefinitions,
  useCardProperties,
  useCreatePropertyDefinition,
  useBulkSetCardProperties,
  useDeletePropertyDefinition,
} from '../../api/queries/propertyQueries.js';
import { useCardTags } from '../../api/queries/tagQueries.js';
import PropertyRow from './PropertyRow.jsx';
import PropertyDefinitionForm from './PropertyDefinitionForm.jsx';
import TagSelector from './TagSelector.jsx';
import './PropertyPanel.css';

export default function PropertyPanel({ boardId, cardId, card, onClose }) {
  const [showAddForm, setShowAddForm] = useState(false);

  const { data: defsData } = usePropertyDefinitions(boardId);
  const { data: valsData } = useCardProperties(boardId, cardId);
  const { data: tagsData } = useCardTags(boardId, cardId);
  const createPropDef = useCreatePropertyDefinition(boardId);
  const bulkSet = useBulkSetCardProperties(boardId);
  const deletePropDef = useDeletePropertyDefinition(boardId);

  const definitions = defsData?.properties || [];
  const cardTags = tagsData?.tags || [];

  // Build a value lookup: { property_id: value }
  const valuesMap = useMemo(() => {
    const map = {};
    for (const v of valsData?.values || []) {
      map[v.property_id] = v.value;
    }
    return map;
  }, [valsData]);

  const handleValueChange = (propId, newValue) => {
    bulkSet.mutate({ cardId, values: { [propId]: newValue } });
  };

  const handleAddProperty = (data) => {
    createPropDef.mutate(data);
    setShowAddForm(false);
  };

  const handleDeleteProperty = (propId) => {
    deletePropDef.mutate(propId);
  };

  if (!cardId) return null;

  return (
    <div className="property-panel">
      <div className="property-panel__header">
        <h3 className="property-panel__title">Properties</h3>
        <button className="property-panel__close" onClick={onClose} type="button">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 6L6 18M6 6l12 12" />
          </svg>
        </button>
      </div>

      {card && (
        <div className="property-panel__card-info">
          <span className="property-panel__card-type">{card.card_type}</span>
          <span className="property-panel__card-title">{card.title || 'Untitled'}</span>
        </div>
      )}

      <div className="property-panel__section">
        <div className="property-panel__section-header">
          <span>Tags</span>
        </div>
        <TagSelector boardId={boardId} cardId={cardId} cardTags={cardTags} />
      </div>

      <div className="property-panel__section">
        <div className="property-panel__section-header">
          <span>Properties</span>
          <button
            className="property-panel__add-btn"
            onClick={() => setShowAddForm(!showAddForm)}
            type="button"
          >
            {showAddForm ? 'Cancel' : '+ Add'}
          </button>
        </div>

        {showAddForm && (
          <PropertyDefinitionForm
            onSubmit={handleAddProperty}
            onCancel={() => setShowAddForm(false)}
          />
        )}

        <div className="property-panel__rows">
          {definitions.map((def) => (
            <div key={def.id} className="property-panel__row-wrapper">
              <PropertyRow
                definition={def}
                value={valuesMap[def.id]}
                onChange={(newVal) => handleValueChange(def.id, newVal)}
              />
              <button
                className="property-panel__row-delete"
                onClick={() => handleDeleteProperty(def.id)}
                title="Delete property"
                type="button"
              >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M18 6L6 18M6 6l12 12" />
                </svg>
              </button>
            </div>
          ))}

          {definitions.length === 0 && !showAddForm && (
            <p className="property-panel__empty">
              No properties defined. Click "+ Add" to create one.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
