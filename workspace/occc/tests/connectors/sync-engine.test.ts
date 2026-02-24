import { afterEach, beforeEach, describe, expect, it } from 'bun:test';
import fs from 'fs/promises';
import path from 'path';
import {
  clearConnectorRuntimeStoreForTests,
  listCheckpointEntries,
  listConnectorStates,
  upsertConnectorState,
} from '../../src/lib/connectors/store';
import { loadCheckpoint, saveCheckpoint } from '../../src/lib/sync/checkpoints';
import { getHealthPriority, pickDominantHealthStatus, sortHealthStatuses } from '../../src/lib/sync/health';
import {
  clearConnectorSyncAdaptersForTests,
  listConnectorProgress,
  runIncrementalSync,
  type ConnectorSyncAdapter,
  type SyncRecord,
} from '../../src/lib/sync/engine';

const testStorePath = path.join(process.cwd(), '.tmp', `connector-runtime-${process.pid}.json`);

describe('connector runtime primitives', () => {
  beforeEach(async () => {
    process.env.CONNECTOR_RUNTIME_STORE_PATH = testStorePath;
    await clearConnectorRuntimeStoreForTests();
  });

  afterEach(async () => {
    await clearConnectorRuntimeStoreForTests();
    clearConnectorSyncAdaptersForTests();
    await fs.rm(path.dirname(testStorePath), { recursive: true, force: true });
    delete process.env.CONNECTOR_RUNTIME_STORE_PATH;
  });

  it('persists checkpoints per connector + source pair', async () => {
    await upsertConnectorState({
      id: 'connector-slack',
      provider: 'slack',
      sources: [
        { sourceId: 'channel-a', sourceType: 'channel', label: 'A' },
        { sourceId: 'channel-b', sourceType: 'channel', label: 'B' },
      ],
      status: 'connected',
      enabled: true,
    });

    await saveCheckpoint({
      connectorId: 'connector-slack',
      sourceId: 'channel-a',
      cursor: { ts: '10.0' },
    });

    await saveCheckpoint({
      connectorId: 'connector-slack',
      sourceId: 'channel-b',
      cursor: { ts: '22.0' },
    });

    const checkpointA = await loadCheckpoint('connector-slack', 'channel-a');
    const checkpointB = await loadCheckpoint('connector-slack', 'channel-b');

    expect(checkpointA?.cursor).toEqual({ ts: '10.0' });
    expect(checkpointB?.cursor).toEqual({ ts: '22.0' });

    const allEntries = await listCheckpointEntries();
    expect(allEntries).toHaveLength(2);
  });

  it('uses required connector health priority ordering', () => {
    expect(getHealthPriority('auth_expired')).toBeGreaterThan(getHealthPriority('error'));
    expect(getHealthPriority('error')).toBeGreaterThan(getHealthPriority('rate_limited'));
    expect(getHealthPriority('rate_limited')).toBeGreaterThan(getHealthPriority('syncing'));
    expect(getHealthPriority('syncing')).toBeGreaterThan(getHealthPriority('connected'));

    const sorted = sortHealthStatuses(['connected', 'rate_limited', 'auth_expired', 'syncing']);
    expect(sorted).toEqual(['auth_expired', 'rate_limited', 'syncing', 'connected']);
    expect(pickDominantHealthStatus(['rate_limited', 'auth_expired'])).toBe('auth_expired');
  });

  it('writes checkpoints only after successful persistence and resumes from the saved cursor', async () => {
    const source = { sourceId: 'channel-a', sourceType: 'channel', label: 'Alpha' };
    const allRecords: Array<SyncRecord & { sequence: number }> = [
      { id: 'm1', payload: { text: 'first' }, sequence: 1 },
      { id: 'm2', payload: { text: 'second' }, sequence: 2 },
      { id: 'm3', payload: { text: 'third' }, sequence: 3 },
      { id: 'm4', payload: { text: 'fourth' }, sequence: 4 },
    ];
    const seenIds: string[] = [];
    let failOnThirdRecord = true;

    await upsertConnectorState({
      id: 'connector-slack',
      provider: 'slack',
      sources: [source],
      status: 'connected',
      enabled: true,
    });

    const adapter: ConnectorSyncAdapter = {
      async listSources() {
        return [source];
      },
      async scanChanges({ checkpoint }) {
        const lastSequence = Number(checkpoint?.cursor.sequence || 0);
        const pending = allRecords.filter(record => record.sequence > lastSequence);
        if (pending.length === 0) {
          return [];
        }

        const firstChunk = pending.slice(0, 2);
        const secondChunk = pending.slice(2);
        const batches = [];

        if (firstChunk.length > 0) {
          batches.push({
            records: firstChunk.map(({ sequence, ...record }) => record),
            scanned: firstChunk.length,
            changed: firstChunk.length,
            nextCursor: { sequence: firstChunk[firstChunk.length - 1].sequence },
          });
        }

        if (secondChunk.length > 0) {
          batches.push({
            records: secondChunk.map(({ sequence, ...record }) => record),
            scanned: secondChunk.length,
            changed: secondChunk.length,
            nextCursor: { sequence: secondChunk[secondChunk.length - 1].sequence },
            retryAttempts: 1,
          });
        }

        return batches;
      },
      async upsertRecords({ records }) {
        const ids = records.map(record => record.id);
        if (failOnThirdRecord && ids.includes('m3')) {
          throw new Error('transient persistence failure');
        }
        seenIds.push(...ids);
        return records.length;
      },
    };

    await expect(
      runIncrementalSync({
        connectorId: 'connector-slack',
        adapter,
      })
    ).rejects.toThrow('transient persistence failure');

    const checkpointAfterFailure = await loadCheckpoint('connector-slack', source.sourceId);
    expect(checkpointAfterFailure?.cursor).toEqual({ sequence: 2 });
    expect(seenIds).toEqual(['m1', 'm2']);

    failOnThirdRecord = false;

    const resumed = await runIncrementalSync({
      connectorId: 'connector-slack',
      adapter,
    });

    expect(resumed.status).toBe('completed');
    expect(resumed.sourceResults[0].counters).toEqual({
      scanned: 2,
      changed: 2,
      upserted: 2,
    });
    expect(seenIds).toEqual(['m1', 'm2', 'm3', 'm4']);

    const checkpointAfterResume = await loadCheckpoint('connector-slack', source.sourceId);
    expect(checkpointAfterResume?.cursor).toEqual({ sequence: 4 });

    const progress = await listConnectorProgress('connector-slack');
    expect(progress).toHaveLength(1);
    expect(progress[0].stage).toBe('completed');
    expect(progress[0].counters).toEqual({ scanned: 2, changed: 2, upserted: 2 });
    expect(progress[0].retry.attempts).toBeGreaterThanOrEqual(0);
  });

  it('normalizes auth and rate limit connector health transitions', async () => {
    const source = { sourceId: 'channel-b', sourceType: 'channel', label: 'Beta' };

    await upsertConnectorState({
      id: 'connector-linear',
      provider: 'linear',
      sources: [source],
      status: 'connected',
      enabled: true,
    });

    await expect(
      runIncrementalSync({
        connectorId: 'connector-linear',
        adapter: {
          async listSources() {
            return [source];
          },
          async scanChanges() {
            return [
              {
                records: [{ id: 'i1', payload: {} }],
                nextCursor: { sequence: 1 },
              },
            ];
          },
          async upsertRecords() {
            throw Object.assign(new Error('unauthorized'), { status: 401 });
          },
        },
      })
    ).rejects.toThrow('unauthorized');

    const [stateAfterAuth] = await listConnectorStates();
    expect(stateAfterAuth.status).toBe('auth_expired');

    await expect(
      runIncrementalSync({
        connectorId: 'connector-linear',
        adapter: {
          async listSources() {
            return [source];
          },
          async scanChanges() {
            return [
              {
                records: [{ id: 'i1', payload: {} }],
                nextCursor: { sequence: 1 },
              },
            ];
          },
          async upsertRecords() {
            throw Object.assign(new Error('throttled'), { status: 429 });
          },
        },
      })
    ).rejects.toThrow('throttled');

    const [stateAfterRateLimit] = await listConnectorStates();
    expect(stateAfterRateLimit.status).toBe('rate_limited');
  });
});
