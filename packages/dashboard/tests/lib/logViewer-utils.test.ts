import { describe, it, expect } from 'vitest';
import { suffixOverlapMerge } from '@/lib/logViewer-utils';
import type { LogEntry } from '@/components/LogViewer';

function entry(line: string, ts = 1000): LogEntry {
  return { line, stream: 'stdout', timestamp: ts };
}

describe('suffixOverlapMerge', () => {
  it('returns live unchanged when supplemental is empty', () => {
    const live = [entry('a'), entry('b')];
    expect(suffixOverlapMerge(live, [])).toEqual(live);
  });

  it('appends non-overlapping supplemental to live', () => {
    const live = [entry('a'), entry('b')];
    const sup = [entry('c'), entry('d')];
    expect(suffixOverlapMerge(live, sup)).toEqual([
      entry('a'), entry('b'), entry('c'), entry('d'),
    ]);
  });

  it('finds suffix overlap and appends only the tail', () => {
    const live = [entry('a'), entry('b'), entry('c')];
    const sup = [entry('b'), entry('c'), entry('d'), entry('e')];
    const result = suffixOverlapMerge(live, sup);
    expect(result.map(e => e.line)).toEqual(['a', 'b', 'c', 'd', 'e']);
  });

  it('handles full overlap (no new lines)', () => {
    const live = [entry('a'), entry('b'), entry('c')];
    const sup = [entry('b'), entry('c')];
    expect(suffixOverlapMerge(live, sup)).toEqual(live);
  });

  it('handles CRLF normalization in comparison', () => {
    const live = [entry('line1'), entry('line2\r')];
    const sup = [entry('line2'), entry('line3')];
    const result = suffixOverlapMerge(live, sup);
    expect(result.map(e => e.line)).toEqual(['line1', 'line2\r', 'line3']);
  });

  it('does not drop legitimate repeated lines', () => {
    const live = [entry('Retrying\u2026'), entry('Retrying\u2026'), entry('Retrying\u2026')];
    const sup = [entry('Retrying\u2026'), entry('Done')];
    // Only the last "Retrying…" suffix should overlap with sup[0]
    const result = suffixOverlapMerge(live, sup);
    expect(result.map(e => e.line)).toEqual([
      'Retrying\u2026', 'Retrying\u2026', 'Retrying\u2026', 'Done',
    ]);
  });

  it('caps append with divider when no overlap and supplemental is large (>500 lines)', () => {
    const live = [entry('live-line')];
    const sup = Array.from({ length: 600 }, (_, i) => entry(`sup-${i}`));
    const result = suffixOverlapMerge(live, sup);
    // Should have live-line + divider + last 500 of sup
    expect(result[0].line).toBe('live-line');
    expect(result[1].line).toBe('\u2014 stored log (partial) \u2014');
    expect(result.length).toBe(1 + 1 + 500);
    expect(result[result.length - 1].line).toBe('sup-599');
  });

  it('appends all when no overlap and supplemental is small (<=500 lines)', () => {
    const live = [entry('live-line')];
    const sup = Array.from({ length: 10 }, (_, i) => entry(`sup-${i}`));
    const result = suffixOverlapMerge(live, sup);
    expect(result.length).toBe(11);
    expect(result[0].line).toBe('live-line');
    expect(result[1].line).toBe('sup-0');
  });
});
