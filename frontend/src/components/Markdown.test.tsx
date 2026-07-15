import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { Markdown } from './Markdown';

function renderHtml(content: string): string {
  const { container } = render(<Markdown content={content} />);
  return container.innerHTML;
}

describe('Markdown Component', () => {
  it('renders a table with a separator row', () => {
    const html = renderHtml('| Mes | Margen |\n|---|---|\n| Ene | 42% |');
    expect(html).toContain('<th>Mes</th>');
    expect(html).toContain('<th>Margen</th>');
    expect(html).toContain('<td>Ene</td>');
    expect(html).toContain('<td>42%</td>');
    expect(html).not.toContain('<td>---</td>');
  });

  it('keeps a first data row that contains hyphens', () => {
    const html = renderHtml('| Mes | Var |\n| -2.3 pp | 1.1 |\n| 2026-06 | x |');
    expect(html).toContain('<td>-2.3 pp</td>');
    expect(html).toContain('<td>1.1</td>');
    expect(html).toContain('<td>2026-06</td>');
  });

  it('renders a table without a separator row', () => {
    const html = renderHtml('| A | B |\n| 1 | 2 |\n| 3 | 4 |');
    expect(html).toContain('<th>A</th>');
    expect(html).toContain('<td>1</td>');
    expect(html).toContain('<td>4</td>');
  });

  it('renders a one-line table instead of dropping it', () => {
    const html = renderHtml('| Solo |');
    expect(html).toContain('<table>');
    expect(html).toContain('<th>Solo</th>');
  });

  it('keeps an all-single-dash data row as data', () => {
    const html = renderHtml('| Mes | Var |\n|---|---|\n| - | - |');
    expect(html).toContain('<td>-</td>');
  });

  it('does not italicize between standalone footnote asterisks', () => {
    const html = renderHtml('*Nota: cifras en USD M\n\n*Fuente: FP&A');
    expect(html).not.toContain('<em>');
    expect(html).toContain('*Nota: cifras en USD M');
    expect(html).toContain('*Fuente: FP&amp;A');
  });

  it('does not italicize between same-line stray asterisks', () => {
    const html = renderHtml('Margen* y EBITDA* ajustados');
    expect(html).not.toContain('<em>');
    expect(html).toContain('Margen* y EBITDA* ajustados');
  });

  it('renders normal emphasis and bold', () => {
    const html = renderHtml('Margen **bruto** y *ajustado* listo');
    expect(html).toContain('<strong>bruto</strong>');
    expect(html).toContain('<em>ajustado</em>');
  });

  it('leaves arithmetic asterisks untouched', () => {
    const html = renderHtml('2 * 3 = 6');
    expect(html).not.toContain('<em>');
    expect(html).toContain('2 * 3 = 6');
  });

  it('escapes HTML to prevent XSS', () => {
    const { container } = render(
      <Markdown content={'<script>alert(1)</script>'} />
    );
    expect(container.querySelector('script')).toBeNull();
    expect(container.innerHTML).toContain('&lt;script&gt;');
  });
});
