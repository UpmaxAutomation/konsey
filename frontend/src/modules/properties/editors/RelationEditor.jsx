import { useState } from 'react';

export default function RelationEditor({ value, onChange }) {
  const [id, setId] = useState(value || '');

  const handleBlur = () => {
    if (id !== (value || '')) {
      onChange(id || null);
    }
  };

  return (
    <input
      type="text"
      className="property-editor property-editor--relation"
      value={id}
      onChange={(e) => setId(e.target.value)}
      onBlur={handleBlur}
      onKeyDown={(e) => e.key === 'Enter' && e.target.blur()}
      placeholder="Card ID"
    />
  );
}
