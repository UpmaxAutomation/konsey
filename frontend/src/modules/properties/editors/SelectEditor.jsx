export default function SelectEditor({ value, onChange, options }) {
  const choices = options?.choices || [];

  return (
    <select
      className="property-editor property-editor--select"
      value={value || ''}
      onChange={(e) => onChange(e.target.value || null)}
    >
      <option value="">-- None --</option>
      {choices.map((c) => (
        <option key={c.value || c} value={c.value || c}>
          {c.label || c.value || c}
        </option>
      ))}
    </select>
  );
}
