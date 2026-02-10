import { useState } from 'react';

export default function UrlEditor({ value, onChange }) {
  const [url, setUrl] = useState(value || '');

  const handleBlur = () => {
    if (url !== (value || '')) {
      onChange(url || null);
    }
  };

  return (
    <input
      type="url"
      className="property-editor property-editor--url"
      value={url}
      onChange={(e) => setUrl(e.target.value)}
      onBlur={handleBlur}
      onKeyDown={(e) => e.key === 'Enter' && e.target.blur()}
      placeholder="https://..."
    />
  );
}
