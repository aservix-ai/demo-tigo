import { useState, useEffect, useRef } from 'react';
import { Header } from './components/Header';
import type { PreflightData } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { ChatWindow } from './components/ChatWindow';
import type { Message } from './components/ChatWindow';
import { ReportViewer } from './components/ReportViewer';
import './App.css';

function App() {
  const [currentTab, setCurrentTab] = useState<'chat' | 'report'>('chat');
  const [preflight, setPreflight] = useState<PreflightData | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [threadId, setThreadId] = useState<string>('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [reportText, setReportText] = useState<string>('');

  // Generate unique thread ID on mount
  useEffect(() => {
    const randomId = Math.random().toString(36).substring(2, 10);
    setThreadId(`tigo-session-${randomId}`);
  }, []);

  // Consecutive failed background polls. A single transient failure
  // (timeout, 429) must not flip the app into degraded mode.
  const failedBackgroundPolls = useRef(0);
  // Last applied ready state. While degraded, background polls escalate to
  // the full check so a lightweight ready:true can never mask a failed LLM
  // ping discovered by a full run.
  const lastReadyRef = useRef<boolean | null>(null);

  const applyPreflightResult = (data: PreflightData, background: boolean) => {
    if (background && !data.ready) {
      failedBackgroundPolls.current += 1;
      // Grace period: keep the previous status until two background polls
      // in a row have failed.
      if (failedBackgroundPolls.current < 2) return;
    } else {
      failedBackgroundPolls.current = 0;
    }
    lastReadyRef.current = data.ready;
    setPreflight(data);
  };

  const runPreflight = async (background: boolean) => {
    if (!background) setIsRefreshing(true);
    // Background polls use the lightweight check that skips the live LLM
    // ping — but only while the app is healthy; once degraded they run the
    // full suite so recovery is verified truthfully.
    const useLight = background && lastReadyRef.current !== false;
    try {
      const response = await fetch(
        useLight ? '/api/preflight?full=false' : '/api/preflight'
      );
      const data = await response.json();
      applyPreflightResult(data, background);
    } catch (err: any) {
      console.error('Preflight check failed:', err);
      applyPreflightResult(
        {
          status: 'error',
          ready: false,
          error: 'Failed to connect to backend server.',
          checks: [
            {
              name: 'API Server Connection',
              passed: false,
              error: 'Could not connect. Is the backend server running?',
            },
          ],
        },
        background
      );
    } finally {
      if (!background) setIsRefreshing(false);
    }
  };

  // Full check: used on mount, by the Header refresh button, and after
  // regenerating data. Its result is applied immediately.
  const checkPreflight = () => runPreflight(false);

  // Run preflight check on mount
  useEffect(() => {
    checkPreflight();

    // Poll preflight status every 2 minutes. Background polls hit the
    // lightweight endpoint and only degrade the UI after two consecutive
    // failures; any success recovers immediately.
    const interval = setInterval(() => runPreflight(true), 120000);
    return () => clearInterval(interval);
  }, []);

  const handleRegenerateData = async () => {
    if (isRegenerating) return;
    setIsRegenerating(true);
    try {
      const response = await fetch('/api/data/regenerate', { method: 'POST' });
      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }
      // The old agent thread memory and the visible report quote
      // pre-regeneration figures, so start a fresh session.
      const randomId = Math.random().toString(36).substring(2, 10);
      setThreadId(`tigo-session-${randomId}`);
      setMessages([]);
      setReportText('');
      alert(
        'Mock dataset regenerated successfully! Chat session and report were reset.'
      );
      await checkPreflight();
    } catch (err: any) {
      alert(`Failed to regenerate data: ${err.message}`);
    } finally {
      setIsRegenerating(false);
    }
  };

  const handleResetChat = () => {
    if (
      window.confirm(
        'Are you sure you want to reset this conversation? This will start a new session.'
      )
    ) {
      const randomId = Math.random().toString(36).substring(2, 10);
      setThreadId(`tigo-session-${randomId}`);
      setMessages([]);
    }
  };

  const hasFailedChecks = preflight && !preflight.ready;
  const failingChecksList =
    preflight?.checks?.filter((c) => !c.passed) || [];

  return (
    <div className="app-container">
      <Header
        preflight={preflight}
        onRefreshPreflight={checkPreflight}
        onRegenerateData={handleRegenerateData}
        isRegenerating={isRegenerating}
        isRefreshing={isRefreshing}
      />

      {hasFailedChecks && (
        <div className="warning-banner" data-testid="warning-banner">
          <div className="warning-banner-header">
            <svg
              className="banner-icon animate-pulse"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
              />
            </svg>
            <h3>System Status: Configuration Errors Detected</h3>
          </div>
          <p className="warning-message">
            The application is in degraded mode. Chat and Report features are
            disabled until all checks pass.
          </p>
          <div className="failing-checks-grid">
            {failingChecksList.map((check, idx) => (
              <div key={idx} className="failing-check-card">
                <span className="check-name">{check.name}</span>
                <span className="check-error-msg">
                  {check.error || 'Failed verification.'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="app-main">
        <Sidebar
          currentTab={currentTab}
          onChangeTab={setCurrentTab}
          threadId={threadId}
          onResetChat={handleResetChat}
        />

        <main className="content-pane">
          {currentTab === 'chat' ? (
            <ChatWindow
              threadId={threadId}
              messages={messages}
              setMessages={setMessages}
              disabled={hasFailedChecks ?? true}
            />
          ) : (
            <ReportViewer
              reportText={reportText}
              setReportText={setReportText}
              disabled={hasFailedChecks ?? true}
            />
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
