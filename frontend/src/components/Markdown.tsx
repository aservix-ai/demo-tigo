import React from 'react';

interface MarkdownProps {
  content: string;
}

// A GFM table separator row: each cell is an optional colon, one or more
// dashes, then an optional colon (e.g. |---|:--:|). Data rows that merely
// contain hyphens (negative variances, dates) do NOT match.
const TABLE_SEPARATOR = /^\|(?:\s*:?-+:?\s*\|)+$/;
// Stray separators inside the body need 2+ dashes per cell so an all-dash
// data row like "| - | - |" is kept as data.
const TABLE_BODY_SEPARATOR = /^\|(?:\s*:?-{2,}:?\s*\|)+$/;

function splitRow(line: string): string[] {
  return line
    .split('|')
    .map((c) => c.trim())
    .filter((_, idx, arr) => idx > 0 && idx < arr.length - 1);
}

function parseTable(lines: string[]): string {
  if (lines.length === 0) return '';
  // First line is always the header; skip the |---| separator when present.
  const hasSeparator = lines.length > 1 && TABLE_SEPARATOR.test(lines[1]);
  const startIndex = hasSeparator ? 2 : 1;

  const headers = splitRow(lines[0]);
  const headerHtml =
    '<thead><tr>' +
    headers.map((h) => `<th>${h}</th>`).join('') +
    '</tr></thead>';

  let bodyHtml = '<tbody>';
  for (let i = startIndex; i < lines.length; i++) {
    if (TABLE_BODY_SEPARATOR.test(lines[i])) continue;
    const cells = splitRow(lines[i]);
    bodyHtml += '<tr>' + cells.map((c) => `<td>${c}</td>`).join('') + '</tr>';
  }
  bodyHtml += '</tbody>';

  return `<div class="table-container"><table>${headerHtml}${bodyHtml}</table></div>`;
}

function renderMarkdown(md: string): string {
  if (!md) return '';
  let html = md;

  // Escape HTML special characters to prevent XSS (tags we generate come after)
  html = html
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  // Headers
  html = html.replace(/^# (.*?)$/gm, '<h1>$1</h1>');
  html = html.replace(/^## (.*?)$/gm, '<h2>$1</h2>');
  html = html.replace(/^### (.*?)$/gm, '<h3>$1</h3>');
  html = html.replace(/^#### (.*?)$/gm, '<h4>$1</h4>');

  // Bold
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  // Italic: delimiters must hug non-whitespace and stay on one line, so
  // stray asterisks (footnote markers) never pair up across the text
  html = html.replace(/\*([^\s*\n](?:[^*\n]*[^\s*\n])?)\*/g, '<em>$1</em>');
  // Inline Code
  html = html.replace(/`(.*?)`/g, '<code>$1</code>');

  // Blockquotes/Alerts
  html = html.replace(/^&gt; (.*?)$/gm, '<blockquote>$1</blockquote>');

  // Tables parsing
  const lines = html.split('\n');
  let inTable = false;
  let tableLines: string[] = [];
  const processedLines: string[] = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (line.startsWith('|') && line.endsWith('|')) {
      if (!inTable) {
        inTable = true;
        tableLines = [];
      }
      tableLines.push(line);
    } else {
      if (inTable) {
        processedLines.push(parseTable(tableLines));
        inTable = false;
      }
      processedLines.push(lines[i]);
    }
  }
  if (inTable) {
    processedLines.push(parseTable(tableLines));
  }

  html = processedLines.join('\n');

  // Lists
  const listLines = html.split('\n');
  let inList = false;
  const listProcessed: string[] = [];
  for (let i = 0; i < listLines.length; i++) {
    const line = listLines[i];
    const match = line.match(/^(\s*)-\s+(.*)$/);
    if (match) {
      if (!inList) {
        listProcessed.push('<ul>');
        inList = true;
      }
      listProcessed.push(`<li>${match[2]}</li>`);
    } else {
      if (inList) {
        listProcessed.push('</ul>');
        inList = false;
      }
      listProcessed.push(line);
    }
  }
  if (inList) {
    listProcessed.push('</ul>');
  }

  html = listProcessed.join('\n');

  // Newlines & paragraphs formatting
  let paragraphs = html.split('\n\n');
  paragraphs = paragraphs.map((p) => {
    const pt = p.trim();
    if (!pt) return '';
    // If it's a block-level element already, don't wrap it
    if (/^<(h1|h2|h3|h4|ul|blockquote|div|table|ol)/i.test(pt)) {
      return pt;
    }
    return `<p>${pt.replace(/\n/g, '<br />')}</p>`;
  });

  return paragraphs.filter(Boolean).join('\n');
}

export const Markdown: React.FC<MarkdownProps> = ({ content }) => {
  const html = React.useMemo(() => renderMarkdown(content), [content]);
  return (
    <div
      className="markdown-content"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
};
