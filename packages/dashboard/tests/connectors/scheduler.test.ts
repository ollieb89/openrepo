import { expect, test, describe, beforeEach, vi } from 'vitest';
import { runBackgroundSync, BACKGROUND_SYNC_INTERVAL_MS } from '@/lib/sync/scheduler';

const mocks = vi.hoisted(() => ({
  listConnectorStates: vi.fn(),
  runIncrementalSync: vi.fn(),
}));

vi.mock('@/lib/connectors/store', () => ({
  listConnectorStates: mocks.listConnectorStates,
}));

vi.mock('@/lib/sync/engine', () => ({
  runIncrementalSync: mocks.runIncrementalSync,
}));

describe('Background Sync Scheduler', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('skips disabled connectors', async () => {
    mocks.listConnectorStates.mockResolvedValue([
      { id: 'c1', enabled: false, status: 'connected', provider: 'slack', sources: [] },
    ]);

    const result = await runBackgroundSync();
    expect(result.triggered).toHaveLength(0);
    expect(result.skipped).toBe(1);
    expect(mocks.runIncrementalSync).not.toHaveBeenCalled();
  });

  test('skips connectors with busy/unhealthy status', async () => {
    mocks.listConnectorStates.mockResolvedValue([
      { id: 'c1', enabled: true, status: 'syncing', provider: 'slack', sources: [] },
      { id: 'c2', enabled: true, status: 'rate_limited', provider: 'slack', sources: [] },
      { id: 'c3', enabled: true, status: 'auth_expired', provider: 'slack', sources: [] },
    ]);

    const result = await runBackgroundSync();
    expect(result.triggered).toHaveLength(0);
    expect(result.skipped).toBe(3);
  });

  test('skips recently synced connectors', async () => {
    const recent = new Date(Date.now() - 1000).toISOString(); // 1 second ago

    mocks.listConnectorStates.mockResolvedValue([
      {
        id: 'c1',
        enabled: true,
        status: 'connected',
        lastSyncedAt: recent,
        provider: 'slack',
        sources: [],
      },
    ]);

    const result = await runBackgroundSync();
    expect(result.triggered).toHaveLength(0);
    expect(result.skipped).toBe(1);
  });

  test('triggers sync for healthy enabled connectors past interval', async () => {
    mocks.runIncrementalSync.mockResolvedValue({});
    const old = new Date(Date.now() - BACKGROUND_SYNC_INTERVAL_MS - 1000).toISOString();
    mocks.listConnectorStates.mockResolvedValue([
      {
        id: 'c1',
        enabled: true,
        status: 'connected',
        lastSyncedAt: old,
        provider: 'slack',
        sources: [],
      },
      {
        id: 'c2',
        enabled: true,
        status: 'connected',
        lastSyncedAt: undefined,
        provider: 'slack',
        sources: [],
      },
    ]);

    const result = await runBackgroundSync();
    expect(result.triggered).toEqual(['c1', 'c2']);
    expect(mocks.runIncrementalSync).toHaveBeenCalledTimes(2);
  });
});
