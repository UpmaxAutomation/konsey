import '../styles/ColorPicker.css';

const COLORS = [
  { key: 'gray', color: 'var(--card-gray)', label: 'Gray' },
  { key: 'red', color: 'var(--card-red)', label: 'Red' },
  { key: 'orange', color: 'var(--card-orange)', label: 'Orange' },
  { key: 'yellow', color: 'var(--card-yellow)', label: 'Yellow' },
  { key: 'green', color: 'var(--card-green)', label: 'Green' },
  { key: 'blue', color: 'var(--card-blue)', label: 'Blue' },
  { key: 'purple', color: 'var(--card-purple)', label: 'Purple' },
  { key: 'pink', color: 'var(--card-pink)', label: 'Pink' },
];

/**
 * ColorPicker - A reusable 8-color picker grid for selecting card and section colors.
 * Renders a 4x2 grid of color swatches with optional "Remove color" action.
 * @param {{ selected: string, onSelect: (key: string|null) => void, showRemove?: boolean }} props
 */
export default function ColorPicker({ selected, onSelect, showRemove = false }) {
  return (
    <div className="color-picker" role="radiogroup" aria-label="Color selection">
      <div className="color-picker__grid">
        {COLORS.map(({ key, color, label }) => (
          <button
            key={key}
            className={`color-picker__swatch ${selected === key ? 'color-picker__swatch--selected' : ''}`}
            style={{ background: color }}
            onClick={() => onSelect(key)}
            title={label}
            aria-label={`Select ${label} color`}
            aria-checked={selected === key}
            role="radio"
          />
        ))}
      </div>
      {showRemove && (
        <button
          className="color-picker__remove"
          onClick={() => onSelect(null)}
        >
          Remove color
        </button>
      )}
    </div>
  );
}

export { COLORS };
