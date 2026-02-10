/**
 * Compact badge for displaying property values on canvas cards.
 * Only renders for visual property types (select, multi_select, date, checkbox).
 */
export default function PropertyBadge({ definition, value }) {
  if (value == null) return null;

  const type = definition.property_type;

  if (type === 'select' && value) {
    const choice = definition.options?.choices?.find((c) => (c.value || c) === value);
    return (
      <span className="canvas-card__badge canvas-card__badge--select">
        {choice?.label || value}
      </span>
    );
  }

  if (type === 'multi_select' && Array.isArray(value) && value.length > 0) {
    return (
      <>
        {value.slice(0, 3).map((v) => {
          const choice = definition.options?.choices?.find((c) => (c.value || c) === v);
          return (
            <span key={v} className="canvas-card__badge canvas-card__badge--select">
              {choice?.label || v}
            </span>
          );
        })}
        {value.length > 3 && (
          <span className="canvas-card__badge canvas-card__badge--more">+{value.length - 3}</span>
        )}
      </>
    );
  }

  if (type === 'date' && value) {
    return (
      <span className="canvas-card__badge canvas-card__badge--date">
        {value}
      </span>
    );
  }

  if (type === 'checkbox') {
    return (
      <span className={`canvas-card__badge canvas-card__badge--checkbox${value ? ' canvas-card__badge--checked' : ''}`}>
        {value ? '\u2713' : '\u2717'}
      </span>
    );
  }

  return null;
}
