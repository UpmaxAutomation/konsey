import { useState } from 'react';

const PROPERTY_TYPES = [
  { value: 'text', label: 'Text' },
  { value: 'number', label: 'Number' },
  { value: 'select', label: 'Select' },
  { value: 'multi_select', label: 'Multi-select' },
  { value: 'date', label: 'Date' },
  { value: 'checkbox', label: 'Checkbox' },
  { value: 'url', label: 'URL' },
  { value: 'email', label: 'Email' },
  { value: 'relation', label: 'Relation' },
];

export default function PropertyDefinitionForm({ onSubmit, onCancel }) {
  const [name, setName] = useState('');
  const [type, setType] = useState('text');
  const [choicesText, setChoicesText] = useState('');

  const needsChoices = type === 'select' || type === 'multi_select';

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!name.trim()) return;

    const data = {
      name: name.trim(),
      property_type: type,
    };

    if (needsChoices && choicesText.trim()) {
      data.options = {
        choices: choicesText
          .split(',')
          .map((c) => c.trim())
          .filter(Boolean)
          .map((c) => ({ value: c, label: c })),
      };
    }

    onSubmit(data);
    setName('');
    setType('text');
    setChoicesText('');
  };

  return (
    <form className="property-def-form" onSubmit={handleSubmit}>
      <input
        className="property-def-form__input"
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Property name"
        autoFocus
      />
      <select
        className="property-def-form__select"
        value={type}
        onChange={(e) => setType(e.target.value)}
      >
        {PROPERTY_TYPES.map((t) => (
          <option key={t.value} value={t.value}>
            {t.label}
          </option>
        ))}
      </select>
      {needsChoices && (
        <input
          className="property-def-form__input"
          value={choicesText}
          onChange={(e) => setChoicesText(e.target.value)}
          placeholder="Options (comma-separated)"
        />
      )}
      <div className="property-def-form__actions">
        <button type="submit" className="property-def-form__btn property-def-form__btn--primary">
          Add
        </button>
        <button type="button" className="property-def-form__btn" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}
