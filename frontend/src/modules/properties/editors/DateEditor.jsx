export default function DateEditor({ value, onChange }) {
  return (
    <input
      type="date"
      className="property-editor property-editor--date"
      value={value || ''}
      onChange={(e) => onChange(e.target.value || null)}
    />
  );
}
