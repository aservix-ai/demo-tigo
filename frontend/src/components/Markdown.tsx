import React from 'react';

interface MarkdownProps {
  content: string;
}

function parseTable(lines: string[]): string {
  if (lines.length < 2) return '';
  // Check if second line is a separator like |---|---|
  const hasSeparator = lines[1].includes('-');
  const startIndex = hasSeparator ? 2 : 1;
  const headers = lines[0]
    .split('|')
    .map((x) => x.trim())
    .filter((_, idx, arr) => idx > 0 && idx < arr.length - 1);

  const headerHtml =
    '<thead><tr>' +
    headers.map((h) => `<th>${h}</th>`).join('') +
    '</tr></thead>';

  let bodyHtml = '<tbody>';
  for (let i = startIndex; i < lines.length; i++) {
    const cells = lines[i]
      .split('|')
      .map((c) => c.trim())
      .filter((_, idx, arr) => idx > 0 && idx < arr.length - 1);
    bodyHtml += '<tr>' + cells.map((c) => `<td>${c}</td>`).join('') + '</tr>';
  }
  bodyHtml += '</tbody>';

  return `<div class="table-container"><table>${headerHtml}${bodyHtml}</table></div>`;
}

function renderMarkdown(md: string): string {
  if (!md) return '';
  let html = md;

  // Replace HTML special characters to prevent XSS (allowing tags we will generate)
  html = html
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  // Headers
  html = html.replace(/^# (.*?)$/gm, '<h1>$1</h1>');
  html = html.replace(/^## (.*?)$/gm, '<h2>$2.5 $1</h2>'); // Wait, let's keep original format
  // Ah, let's just do standard header replacement:
  html = md // Let's use md directly or escape it and then format.
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  // Parse Headers
  html = html.replace(/^# (.*?)$/gm, '<h1>$1</h1>');
  html = html.replace(/^## (.*?)$/gm, '<h2>$1</h2>');
  html = html.replace(/^### (.*?)$/gm, '<h3>$1</h3>');
  html = html.replace(/^#### (.*?)$/gm, '<h4>$1</h4>');

  // Bold
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  // Italic
  html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
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
