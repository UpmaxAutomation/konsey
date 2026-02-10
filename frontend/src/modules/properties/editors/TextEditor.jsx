import { useState } from 'react';

export default function TextEditor({ value, onChange }) {
  const [text, setText] = useState(value || '');

  const handleBlur = () => {
    if (text !== (value || '')) {
      onChange(text);
    }
  };

  return (
    <input
      type="text"
      className="property-editor property-editor--text"
      value={text}
      onChange={(e) => setText(e.target.value)}
      onBlur={handleBlur}
      onKeyDown={(e) => e.key === 'Enter' && e.target.blur()}
      placeholder="Empty"
    />
  );
}
