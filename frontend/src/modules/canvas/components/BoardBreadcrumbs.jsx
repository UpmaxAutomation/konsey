import '../styles/BoardBreadcrumbs.css';

/**
 * BoardBreadcrumbs - Navigation breadcrumb trail for board hierarchy.
 * Shows clickable parent boards and the current board name.
 * Only renders when there are 2+ items in the trail.
 * @param {{ breadcrumbs: Array<{ id: string, name: string, icon?: string }>, onNavigate: (id: string) => void }} props
 */
export default function BoardBreadcrumbs({ breadcrumbs = [], onNavigate }) {
  if (!breadcrumbs || breadcrumbs.length <= 1) return null;

  return (
    <nav className="board-breadcrumbs" aria-label="Board navigation">
      {breadcrumbs.map((crumb, i) => (
        <span key={crumb.id} className="board-breadcrumbs__item">
          {i > 0 && (
            <svg
              className="board-breadcrumbs__separator"
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              aria-hidden="true"
            >
              <path d="M9 18l6-6-6-6" />
            </svg>
          )}
          {i < breadcrumbs.length - 1 ? (
            <button
              className="board-breadcrumbs__link"
              onClick={() => onNavigate?.(crumb.id)}
            >
              {crumb.icon && (
                <span className="board-breadcrumbs__icon" aria-hidden="true">
                  {crumb.icon}
                </span>
              )}
              {crumb.name}
            </button>
          ) : (
            <span className="board-breadcrumbs__current" aria-current="page">
              {crumb.icon && (
                <span className="board-breadcrumbs__icon" aria-hidden="true">
                  {crumb.icon}
                </span>
              )}
              {crumb.name}
            </span>
          )}
        </span>
      ))}
    </nav>
  );
}
