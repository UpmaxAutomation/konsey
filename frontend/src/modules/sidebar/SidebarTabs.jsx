import './styles/SidebarTabs.css';

const TABS = [
  { key: 'chats', label: 'Chats', icon: 'M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z' },
  { key: 'boards', label: 'Boards', icon: 'M3 3h18v18H3zM3 9h18M9 21V9' },
];

export default function SidebarTabs({ activeTab, onTabChange }) {
  return (
    <div className="sidebar-tabs">
      {TABS.map((tab) => (
        <button
          key={tab.key}
          className={`sidebar-tabs__tab ${activeTab === tab.key ? 'sidebar-tabs__tab--active' : ''}`}
          onClick={() => onTabChange(tab.key)}
          title={tab.label}
          aria-label={tab.label}
          aria-selected={activeTab === tab.key}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d={tab.icon} />
          </svg>
          <span>{tab.label}</span>
        </button>
      ))}
    </div>
  );
}
