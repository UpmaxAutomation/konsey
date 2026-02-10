import { useState } from 'react';

export default function NumberEditor({ value, onChange }) {
  const [num, setNum] = useState(value ?? '');

  const handleBlur = () => {
    const parsed = num === '' ? null : Number(num);
    if (parsed !== value) {
      onChange(parsed);
    }
  };

  return (
    <input
      type="number"
      className="property-editor property-editor--number"
      value={num}
      onChange={(e) => setNum(e.target.value)}
      onBlur={handleBlur}
      onKeyDown={(e) => e.key === 'Enter' && e.target.blur()}
      placeholder="Empty"
    />
  );
}
