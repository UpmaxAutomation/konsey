import { useState } from 'react';

export default function EmailEditor({ value, onChange }) {
  const [email, setEmail] = useState(value || '');

  const handleBlur = () => {
    if (email !== (value || '')) {
      onChange(email || null);
    }
  };

  return (
    <input
      type="email"
      className="property-editor property-editor--email"
      value={email}
      onChange={(e) => setEmail(e.target.value)}
      onBlur={handleBlur}
      onKeyDown={(e) => e.key === 'Enter' && e.target.blur()}
      placeholder="user@example.com"
    />
  );
}
