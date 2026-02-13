import './styles/SidebarTabs.css';

const TABS = [
  { key: 'chats', label: 'Chats', icon: 'M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z' },
  { key: 'boards', label: 'Boards', icon: 'M3 3h18v18H3zM3 9h18M9 21V9' },
  { key: 'cards', label: 'Cards', icon: 'M19 3H5a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2V5a2 2 0 00-2-2zM5 3v18' },
  { key: 'journal', label: 'Journal', icon: 'M4 19.5A2.5 2.5 0 016.5 17H20M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z' },
  { key: 'inbox', label: 'Inbox', icon: 'M22 12l-6 0-2 3-4 0-2-3-6 0M5.45 5.11L2 12v6a2 2 0 002 2h16a2 2 0 002-2v-6l-3.45-6.89A2 2 0 0016.76 4H7.24a2 2 0 00-1.79 1.11z' },
  { key: 'tags', label: 'Tags', icon: 'M20.59 13.41l-7.17 7.17a2 2 0 01-2.83 0L2 12V2h10l8.59 8.59a2 2 0 010 2.82zM7 7h.01' },
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
