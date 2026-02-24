import { expect, test, describe, beforeEach, mock } from 'bun:test';
import { runBackgroundSync, BACKGROUND_SYNC_INTERVAL_MS } from '@/lib/sync/scheduler';
import { listConnectorStates } from '@/lib/connectors/store';
import { runIncrementalSync } from '@/lib/sync/engine';

// Mock dependencies
mock.module('@/lib/connectors/store', () => ({
  listConnectorStates: mock(() => []),
}));

mock.module('@/lib/sync/engine', () => ({
  runIncrementalSync: mock(async () => ({})),
}));

describe('Background Sync Scheduler', () => {
  beforeEach(() => {
    mock.restore();
  });

  test('skips disabled connectors', async () => {
    const { listConnectorStates } = await import('@/lib/connectors/store');
    const { runIncrementalSync } = await import('@/lib/sync/engine');

    (listConnectorStates as any).mockResolvedValue([
      { id: 'c1', enabled: false, status: 'connected', provider: 'slack', sources: [] },
    ]);

    const result = await runBackgroundSync();
    expect(result.triggered).toHaveLength(0);
    expect(result.skipped).toBe(1);
    expect(runIncrementalSync).not.toHaveBeenCalled();
  });

  test('skips connectors with busy/unhealthy status', async () => {
    const { listConnectorStates } = await import('@/lib/connectors/store');

    (listConnectorStates as any).mockResolvedValue([
      { id: 'c1', enabled: true, status: 'syncing', provider: 'slack', sources: [] },
      { id: 'c2', enabled: true, status: 'rate_limited', provider: 'slack', sources: [] },
      { id: 'c3', enabled: true, status: 'auth_expired', provider: 'slack', sources: [] },
    ]);

    const result = await runBackgroundSync();
    expect(result.triggered).toHaveLength(0);
    expect(result.skipped).toBe(3);
  });

  test('skips recently synced connectors', async () => {
    const { listConnectorStates } = await import('@/lib/connectors/store');
    const recent = new Date(Date.now() - 1000).toISOString(); // 1 second ago
    
    (listConnectorStates as any).mockResolvedValue([
      { id: 'c1', enabled: true, status: 'connected', lastSyncedAt: recent, provider: 'slack', sources: [] },
    ]);

    const result = await runBackgroundSync();
    expect(result.triggered).toHaveLength(0);
    expect(result.skipped).toBe(1);
  });

  test('triggers sync for healthy enabled connectors past interval', async () => {
    const { listConnectorStates } = await import('@/lib/connectors/store');
    const { runIncrementalSync } = await import('@/lib/sync/engine');
    
    const old = new Date(Date.now() - BACKGROUND_SYNC_INTERVAL_MS - 1000).toISOString();
    (listConnectorStates as any).mockResolvedValue([
      { id: 'c1', enabled: true, status: 'connected', lastSyncedAt: old, provider: 'slack', sources: [] },
      { id: 'c2', enabled: true, status: 'connected', lastSyncedAt: undefined, provider: 'slack', sources: [] },
    ]);

    const result = await runBackgroundSync();
    expect(result.triggered).toEqual(['c1', 'c2']);
    expect(runIncrementalSync).toHaveBeenCalledTimes(2);
  });
});
