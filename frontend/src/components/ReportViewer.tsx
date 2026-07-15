import React, { useState } from 'react';
import { Markdown } from './Markdown';

interface ReportViewerProps {
  reportText: string;
  setReportText: React.Dispatch<React.SetStateAction<string>>;
  disabled: boolean;
}

export const ReportViewer: React.FC<ReportViewerProps> = ({
  reportText,
  setReportText,
  disabled,
}) => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGenerateReport = async () => {
    if (isLoading || disabled) return;

    setIsLoading(true);
    setError(null);
    // Keep the current report until a successful response replaces it, so a
    // failed regeneration does not destroy the on-screen report.

    try {
      const response = await fetch('/api/report', {
        method: 'POST',
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.error || `HTTP error ${response.status}`);
      }

      const data = await response.json();
      if (data.status === 'success') {
        setReportText(data.report);
      } else {
        throw new Error(data.error || 'Failed to generate report');
      }
    } catch (err: any) {
      console.error('Report error:', err);
      setError(err.message || 'An error occurred during report generation.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopy = async () => {
    if (!reportText) return;
    let copied = false;
    if (navigator.clipboard && window.isSecureContext) {
      try {
        await navigator.clipboard.writeText(reportText);
        copied = true;
      } catch (err) {
        console.error('Clipboard API copy failed:', err);
      }
    }
    if (!copied) {
      // Fallback for non-secure origins (e.g. LAN demo over plain http),
      // where navigator.clipboard is unavailable.
      const textarea = document.createElement('textarea');
      textarea.value = reportText;
      textarea.style.position = 'fixed';
      textarea.style.opacity = '0';
      document.body.appendChild(textarea);
      textarea.select();
      try {
        copied = document.execCommand('copy');
      } catch (err) {
        console.error('Fallback copy failed:', err);
      }
      document.body.removeChild(textarea);
    }
    alert(
      copied
        ? 'Report copied to clipboard!'
        : 'Failed to copy report to clipboard.'
    );
  };

  return (
    <div className="report-viewer">
      <div className="report-controls">
        <h2>Executive Financial Report</h2>
        <div className="btn-group">
          {reportText && (
            <button
              onClick={handleCopy}
              className="btn btn-secondary btn-icon"
              data-testid="copy-btn"
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
                  d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9a.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.25c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184"
                />
              </svg>
              <span>Copy Markdown</span>
            </button>
          )}

          <button
            onClick={handleGenerateReport}
            disabled={isLoading || disabled}
            className="btn btn-primary btn-icon"
            data-testid="generate-report-btn"
          >
            <svg
              className={`icon ${isLoading ? 'spin' : ''}`}
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m.75 12H9m3 0h.008v.008H12v-.008zM12 15h.008v.008H12V15zm0 2.25h.008v.008H12v-.008zM9.75 15h.008v.008H9.75V15zm0 2.25h.008v.008H9.75v-.008zM7.5 15h.008v.008H7.5V15zm0 2.25h.008v.008H7.5v-.008zm6.75-4.5h.008v.008h-.008v-.008zm0 2.25h.008v.008h-.008V15zm0 2.25h.008v.008h-.008v-.008zm2.25-4.5h.008v.008H16.5v-.008zm0 2.25h.008v.008H16.5V15z"
              />
            </svg>
            <span>
              {isLoading ? 'Generating...' : 'Generate June 2026 Report'}
            </span>
          </button>
        </div>
      </div>

      <div className="report-content-area">
        {isLoading ? (
          <div className="report-loading-screen" data-testid="report-loading">
            <div className="loading-spinner-glow"></div>
            <div className="loading-spinner"></div>
            <h3>Running report tools...</h3>
            <p>
              Calling financial databases, checking CAPEX allocations,
              retrieving collection statuses, and scanning active risk alarms.
            </p>
          </div>
        ) : (
          <>
            {error && (
              <div
                className={`report-error-box${
                  reportText ? ' report-error-inline' : ''
                }`}
              >
                <svg
                  className="error-icon"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"
                  />
                </svg>
                <h3>Report Generation Failed</h3>
                <p>{error}</p>
                {reportText && (
                  <p>The previously generated report is preserved below.</p>
                )}
                <button
                  onClick={handleGenerateReport}
                  className="btn btn-primary mt-4"
                >
                  Try Again
                </button>
              </div>
            )}
            {reportText ? (
              <div className="report-paper">
                <Markdown content={reportText} />
              </div>
            ) : (
              !error && (
                <div className="report-empty-state">
                  <svg
                    className="empty-icon"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
                    />
                  </svg>
                  <h3>No Report Generated</h3>
                  <p>
                    Click the "Generate June 2026 Report" button above to run the
                    analysis pipeline and build the executive FP&A report.
                  </p>
                </div>
              )
            )}
          </>
        )}
      </div>
    </div>
  );
};
