export default function CheckboxEditor({ value, onChange }) {
  return (
    <label className="property-editor property-editor--checkbox">
      <input
        type="checkbox"
        checked={!!value}
        onChange={(e) => onChange(e.target.checked)}
      />
      <span>{value ? 'Yes' : 'No'}</span>
    </label>
  );
}
