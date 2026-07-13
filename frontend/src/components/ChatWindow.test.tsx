import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ChatWindow } from './ChatWindow';

describe('ChatWindow Component', () => {
  it('renders the welcome message when there are no messages', () => {
    const setMessages = vi.fn();
    render(
      <ChatWindow
        threadId="test-thread"
        messages={[]}
        setMessages={setMessages}
        disabled={false}
      />
    );

    expect(screen.getByText('FP&A Assistant')).toBeDefined();
    expect(
      screen.getByPlaceholderText('Type your financial query...')
    ).toBeDefined();
  });

  it('renders conversation history and message bubbles correctly', () => {
    const setMessages = vi.fn();
    const mockMessages = [
      { role: 'user' as const, content: 'Hello AI' },
      { role: 'assistant' as const, content: 'Hello User', tools: [] },
    ];

    render(
      <ChatWindow
        threadId="test-thread"
        messages={mockMessages}
        setMessages={setMessages}
        disabled={false}
      />
    );

    expect(screen.getByText('Hello AI')).toBeDefined();
    expect(screen.getByText('Hello User')).toBeDefined();
  });

  it('disables input when the component is disabled', () => {
    const setMessages = vi.fn();
    render(
      <ChatWindow
        threadId="test-thread"
        messages={[]}
        setMessages={setMessages}
        disabled={true}
      />
    );

    const input = screen.getByPlaceholderText(
      'Fix preflight errors to enable chat...'
    );
    expect((input as HTMLInputElement).disabled).toBe(true);
  });
});
