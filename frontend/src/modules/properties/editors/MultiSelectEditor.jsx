export default function MultiSelectEditor({ value, onChange, options }) {
  const choices = options?.choices || [];
  const selected = Array.isArray(value) ? value : [];

  const toggle = (val) => {
    const next = selected.includes(val)
      ? selected.filter((v) => v !== val)
      : [...selected, val];
    onChange(next);
  };

  return (
    <div className="property-editor property-editor--multi-select">
      {choices.map((c) => {
        const val = c.value || c;
        const label = c.label || c.value || c;
        const isActive = selected.includes(val);
        return (
          <button
            key={val}
            className={`property-editor__chip${isActive ? ' property-editor__chip--active' : ''}`}
            onClick={() => toggle(val)}
            type="button"
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}
