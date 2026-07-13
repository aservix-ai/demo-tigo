import React from 'react';

interface SidebarProps {
  currentTab: 'chat' | 'report';
  onChangeTab: (tab: 'chat' | 'report') => void;
  threadId: string;
  onResetChat: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onChangeTab,
  threadId,
  onResetChat,
}) => {
  return (
    <aside className="app-sidebar">
      <div className="sidebar-nav">
        <button
          onClick={() => onChangeTab('chat')}
          className={`nav-item ${currentTab === 'chat' ? 'active' : ''}`}
        >
          <svg
            className="nav-icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
            />
          </svg>
          <span className="nav-label">Q&A Chat</span>
        </button>

        <button
          onClick={() => onChangeTab('report')}
          className={`nav-item ${currentTab === 'report' ? 'active' : ''}`}
        >
          <svg
            className="nav-icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
            />
          </svg>
          <span className="nav-label">Gross Margin Report</span>
        </button>
      </div>

      <div className="sidebar-footer">
        <div className="session-info">
          <div className="session-title">Session Details</div>
          <div className="session-value" title={threadId}>
            <span>Thread:</span>
            <code className="thread-code">{threadId}</code>
          </div>
        </div>

        {currentTab === 'chat' && (
          <button
            onClick={onResetChat}
            className="btn btn-danger w-full btn-icon"
          >
            <svg
              className="icon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99"
              />
            </svg>
            <span>Reset Chat</span>
          </button>
        )}
      </div>
    </aside>
  );
};
