import { describe, it, expect } from 'vitest';
import { getOsloDateString, aggregateTodayUsage } from '@/app/api/metrics/usage-aggregator';

describe('getOsloDateString', () => {
  it('returns YYYY-MM-DD format', () => {
    const result = getOsloDateString(new Date('2026-03-05T11:00:00.000Z'));
    expect(result).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(result).toBe('2026-03-05');
  });

  it('accounts for Oslo timezone — UTC 23:30 Dec 31 is Jan 1 in Oslo (UTC+1)', () => {
    // UTC 23:30 Dec 31 2025 = 00:30 Jan 1 2026 in Oslo (UTC+1 winter)
    const result = getOsloDateString(new Date('2025-12-31T23:30:00.000Z'));
    expect(result).toBe('2026-01-01');
  });
});

describe('aggregateTodayUsage', () => {
  it('sums tokens and cost for today only', () => {
    const today = getOsloDateString(new Date());
    const todayDate = new Date();
    // Manufacture a timestamp that falls on today in Oslo
    const lines = [
      JSON.stringify({ type: 'model.usage', ts: todayDate.toISOString(), usage: { totalTokens: 100 }, costUsd: 0.01 }),
      JSON.stringify({ type: 'model.usage', ts: '2020-01-01T12:00:00.000Z', usage: { totalTokens: 999 }, costUsd: 9.99 }),
    ];
    const result = aggregateTodayUsage(lines);
    expect(result.tokens).toBe(100);
    expect(result.costUsd).toBeCloseTo(0.01);
    expect(result.badLines).toBe(0);
  });

  it('falls back to inputTokens + outputTokens when totalTokens absent', () => {
    const ts = new Date().toISOString();
    const lines = [
      JSON.stringify({ type: 'model.usage', ts, usage: { inputTokens: 40, outputTokens: 20 }, costUsd: 0 }),
    ];
    const result = aggregateTodayUsage(lines);
    expect(result.tokens).toBe(60);
  });

  it('skips non model.usage types', () => {
    const ts = new Date().toISOString();
    const lines = [
      JSON.stringify({ type: 'heartbeat', ts, usage: { totalTokens: 500 }, costUsd: 1 }),
    ];
    const result = aggregateTodayUsage(lines);
    expect(result.tokens).toBe(0);
    expect(result.costUsd).toBe(0);
  });

  it('counts bad lines but does not throw', () => {
    const ts = new Date().toISOString();
    const lines = [
      'not json at all',
      '',
      JSON.stringify({ type: 'model.usage', ts, usage: { totalTokens: 50 }, costUsd: 0.005 }),
    ];
    const result = aggregateTodayUsage(lines);
    expect(result.tokens).toBe(50);
    expect(result.badLines).toBe(1);
  });

  it('returns zeros for empty input', () => {
    const result = aggregateTodayUsage([]);
    expect(result.tokens).toBe(0);
    expect(result.costUsd).toBe(0);
    expect(result.badLines).toBe(0);
  });
});
