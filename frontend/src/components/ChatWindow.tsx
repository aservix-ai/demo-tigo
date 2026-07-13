import React, { useState, useRef, useEffect } from 'react';
import { Markdown } from './Markdown';

export interface ToolCall {
  name: string;
  args: any;
}

export interface Message {
  role: 'user' | 'assistant';
  content: string;
  tools?: ToolCall[];
}

interface ChatWindowProps {
  threadId: string;
  messages: Message[];
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
  disabled: boolean;
}

export const ChatWindow: React.FC<ChatWindowProps> = ({
  threadId,
  messages,
  setMessages,
  disabled,
}) => {
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [activeTools, setActiveTools] = useState<ToolCall[]>([]);
  const [error, setError] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    if (messagesEndRef.current && typeof messagesEndRef.current.scrollIntoView === 'function') {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, activeTools, isLoading]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading || disabled) return;

    const userText = input.trim();
    setInput('');
    setIsLoading(true);
    setError(null);
    setActiveTools([]);

    // Add user message
    setMessages((prev) => [...prev, { role: 'user', content: userText }]);

    // Add initial empty assistant message
    setMessages((prev) => [
      ...prev,
      { role: 'assistant', content: '', tools: [] },
    ]);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: userText, thread_id: threadId }),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.error || `HTTP error ${response.status}`);
      }

      if (!response.body) {
        throw new Error('No response body to stream');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split('\n\n');
        buffer = parts.pop() || '';

        for (const part of parts) {
          const lines = part.split('\n');
          let dataStr = '';

          for (const line of lines) {
            if (line.startsWith('data:')) {
              dataStr = line.slice(5).trim();
            }
          }

          if (dataStr) {
            try {
              const payload = JSON.parse(dataStr);
              if (payload.type === 'token') {
                setMessages((prev) => {
                  const updated = [...prev];
                  const last = updated[updated.length - 1];
                  if (last && last.role === 'assistant') {
                    last.content += payload.content;
                  }
                  return updated;
                });
              } else if (payload.type === 'tool') {
                const tc: ToolCall = {
                  name: payload.name,
                  args: payload.args,
                };
                setActiveTools((prev) => [...prev, tc]);
                setMessages((prev) => {
                  const updated = [...prev];
                  const last = updated[updated.length - 1];
                  if (last && last.role === 'assistant') {
                    last.tools = [...(last.tools || []), tc];
                  }
                  return updated;
                });
              } else if (payload.type === 'error') {
                setError(payload.content);
              } else if (payload.type === 'done') {
                // Done event
              }
            } catch (err) {
              console.error('SSE JSON parse error:', err);
            }
          }
        }
      }
    } catch (err: any) {
      console.error('Chat error:', err);
      setError(err.message || 'An unexpected error occurred.');
      setMessages((prev) => {
        const updated = [...prev];
        const last = updated[updated.length - 1];
        if (
          last &&
          last.role === 'assistant' &&
          !last.content &&
          (!last.tools || last.tools.length === 0)
        ) {
          updated.pop();
        }
        return updated;
      });
    } finally {
      setIsLoading(false);
      setActiveTools([]);
    }
  };

  return (
    <div className="chat-window">
      <div className="messages-container">
        {messages.length === 0 ? (
          <div className="chat-welcome">
            <div className="welcome-icon">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M9.813 15.904L9 21l8.904-4.43c2.285-.5 3.96-2.514 3.96-4.837 0-2.76-2.46-5-5.5-5-1.258 0-2.418.375-3.376 1.014"
                />
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M15.25 10c0 .69-.56 1.25-1.25 1.25s-1.25-.56-1.25-1.25.56-1.25 1.25-1.25 1.25.56 1.25 1.25z"
                />
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M9 10c0 .69-.56 1.25-1.25 1.25S6.5 10.69 6.5 10s.56-1.25 1.25-1.25S9 9.31 9 10z"
                />
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5"
                />
              </svg>
            </div>
            <h2>FP&A Assistant</h2>
            <p>
              Ask questions about revenue, margins, capex, collections, or
              budgets for any Tigo country (Guatemala, Colombia, Bolivia,
              Paraguay, Panamá).
            </p>
            <div className="quick-prompts">
              <button
                onClick={() => setInput('¿Cuáles son los costos directos de Bolivia?')}
                className="btn-quick-prompt"
              >
                "Costos directos de Bolivia"
              </button>
              <button
                onClick={() =>
                  setInput('Muéstrame las alertas detectadas de severidad alta')
                }
                className="btn-quick-prompt"
              >
                "Alertas de severidad alta"
              </button>
              <button
                onClick={() =>
                  setInput('¿Cómo va el consumo de OPEX y CAPEX en Colombia?')
                }
                className="btn-quick-prompt"
              >
                "Consumo OPEX/CAPEX en Colombia"
              </button>
            </div>
          </div>
        ) : (
          messages.map((msg, index) => (
            <div key={index} className={`message-row ${msg.role}`}>
              <div className="message-avatar">
                {msg.role === 'user' ? 'U' : 'AI'}
              </div>
              <div className="message-bubble-wrapper">
                <div className="message-sender">
                  {msg.role === 'user' ? 'You' : 'Tigo FP&A Agent'}
                </div>

                {msg.tools && msg.tools.length > 0 && (
                  <div className="message-tools-list">
                    {msg.tools.map((t, tidx) => (
                      <div key={tidx} className="tool-badge">
                        <svg
                          className="tool-icon"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            d="M11.42 15.17L17.25 21A1.24 1.24 0 1019 19.25l-5.83-5.83M11.42 15.17l2.42-2.42M11.42 15.17L10 16.58A1.79 1.79 0 017.77 15l-1.39-1.39a1.79 1.79 0 010-2.53l1.41-1.41A1.79 1.79 0 0110.33 9l1.39 1.39a1.79 1.79 0 010 2.53L10.3 14.33"
                          />
                        </svg>
                        <span>
                          Used Tool: <strong>{t.name}</strong>
                        </span>
                        <span className="tool-args-preview">
                          {JSON.stringify(t.args)}
                        </span>
                      </div>
                    ))}
                  </div>
                )}

                <div className="message-bubble">
                  {msg.content ? (
                    <Markdown content={msg.content} />
                  ) : (
                    isLoading &&
                    index === messages.length - 1 && (
                      <div className="typing-indicator" data-testid="typing-indicator">
                        <span></span>
                        <span></span>
                        <span></span>
                      </div>
                    )
                  )}
                </div>
              </div>
            </div>
          ))
        )}

        {isLoading && activeTools.length > 0 && (
          <div className="active-tool-indicator-row">
            <div className="pulse-indicator"></div>
            <div className="tool-indicator-text">
              Executing database tools... Running{' '}
              <strong>{activeTools[activeTools.length - 1].name}</strong>
            </div>
          </div>
        )}

        {error && (
          <div className="chat-error-banner">
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
            <div className="error-text">
              <strong>Error:</strong> {error}
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSubmit} className="chat-input-area">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={isLoading || disabled}
          placeholder={
            disabled
              ? 'Fix preflight errors to enable chat...'
              : 'Type your financial query...'
          }
          className="chat-input"
        />
        <button
          type="submit"
          disabled={isLoading || !input.trim() || disabled}
          className="btn btn-primary btn-chat-submit"
        >
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5"
            />
          </svg>
        </button>
      </form>
    </div>
  );
};
