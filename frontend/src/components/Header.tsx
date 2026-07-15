import React from 'react';

export interface Check {
  name: string;
  passed: boolean;
  error: string | null;
}

export interface PreflightData {
  status: string;
  ready: boolean;
  error?: string;
  checks?: Check[];
}

interface HeaderProps {
  preflight: PreflightData | null;
  onRefreshPreflight: () => void;
  onRegenerateData: () => void;
  isRegenerating: boolean;
  isRefreshing: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  preflight,
  onRefreshPreflight,
  onRegenerateData,
  isRegenerating,
  isRefreshing,
}) => {
  const isReady = preflight?.ready ?? false;

  return (
    <header className="app-header">
      <div className="header-left">
        <div className="logo-container">
          <div className="logo-glow"></div>
          <svg
            className="app-logo"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"
            />
          </svg>
          <h1>
            Tigo LatAm <span className="text-gradient">FP&A Suite</span>
          </h1>
        </div>
      </div>

      <div className="header-right">
        {/* Status Indicator */}
        <div
          className={`status-pill ${isReady ? 'status-ready' : 'status-error'}`}
        >
          <span className="status-dot"></span>
          <span className="status-text">
            {isReady ? 'System Ready' : 'System Not Ready'}
          </span>
        </div>

        <button
          onClick={onRefreshPreflight}
          disabled={isRefreshing}
          className="btn btn-secondary btn-icon"
          title="Re-run Preflight Checks"
        >
          <svg
            className={`icon ${isRefreshing ? 'spin' : ''}`}
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
          <span>{isRefreshing ? 'Checking...' : 'Preflight'}</span>
        </button>

        <button
          onClick={onRegenerateData}
          disabled={isRegenerating}
          className="btn btn-primary btn-icon"
          title="Regenerate Mock Datasets"
        >
          <svg
            className={`icon ${isRegenerating ? 'spin' : ''}`}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M19.5 12c0-1.232-.046-2.453-.138-3.662a4.006 4.006 0 00-3.7-3.7 48.678 48.678 0 00-7.324 0 4.006 4.006 0 00-3.7 3.7C4.547 9.547 4.5 10.768 4.5 12s.047 2.453.138 3.662a4.006 4.006 0 003.7 3.7 48.656 48.656 0 007.324 0 4.006 4.006 0 003.7-3.7c.092-1.209.138-2.43.138-3.662z"
            />
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M9 10.5l3 3 3-3"
            />
          </svg>
          <span>{isRegenerating ? 'Regenerating...' : 'Regen Data'}</span>
        </button>
      </div>
    </header>
  );
};
