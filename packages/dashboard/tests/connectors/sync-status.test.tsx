import { describe, expect, it } from 'bun:test';
import type { ConnectorCheckpoint, ConnectorState, SyncProgressSnapshot } from '../../src/lib/types/connectors';
import { buildConnectorHealthPayload } from '../../src/lib/connectors/health-payload';
import {
  reconnectHref,
  resolveSyncEndpoint,
  sortStatusesByPriority,
  statusTrafficLight,
  type SyncConnectorSnapshot,
} from '../../src/lib/hooks/useSyncStatus';

describe('sync status health aggregation', () => {
  it('preserves required status priority ordering', () => {
    const sorted = sortStatusesByPriority(['connected', 'rate_limited', 'auth_expired', 'syncing', 'error']);
    expect(sorted).toEqual(['auth_expired', 'error', 'rate_limited', 'syncing', 'connected']);

    expect(statusTrafficLight('auth_expired')).toBe('red');
    expect(statusTrafficLight('error')).toBe('red');
    expect(statusTrafficLight('rate_limited')).toBe('amber');
    expect(statusTrafficLight('syncing')).toBe('blue');
    expect(statusTrafficLight('connected')).toBe('green');
  });

  it('maps connector sync actions to provider-specific endpoints', () => {
    expect(resolveSyncEndpoint({ id: 'connector-slack-primary', provider: 'slack' } as SyncConnectorSnapshot)).toBe(
      '/api/connectors/slack/sync'
    );
    expect(resolveSyncEndpoint({ id: 'connector-tracker', provider: 'github' } as SyncConnectorSnapshot)).toBe(
      '/api/connectors/tracker/sync'
    );
    expect(resolveSyncEndpoint({ id: 'connector-custom', provider: 'custom' } as SyncConnectorSnapshot)).toBe(
      '/api/connectors/connector-custom/sync'
    );

    expect(reconnectHref({ id: 'connector-slack-primary', provider: 'slack' } as SyncConnectorSnapshot)).toBe(
      '/settings/connectors#slack-connector'
    );
    expect(reconnectHref({ id: 'connector-tracker', provider: 'linear' } as SyncConnectorSnapshot)).toBe(
      '/settings/connectors#tracker-connector'
    );
  });

  it('builds aggregate counters, throughput, and recovery metadata for dashboards', () => {
    const connectors: ConnectorState[] = [
      {
        id: 'connector-slack-primary',
        provider: 'slack',
        sources: [{ sourceId: 'C01', sourceType: 'channel', label: 'general' }],
        status: 'rate_limited',
        enabled: true,
        createdAt: '2026-02-24T10:00:00.000Z',
        updatedAt: '2026-02-24T10:30:00.000Z',
        lastSyncedAt: '2026-02-24T10:20:00.000Z',
        lastError: 'throttled',
      },
      {
        id: 'connector-tracker',
        provider: 'github',
        sources: [{ sourceId: 'acme/repo', sourceType: 'repo', label: 'acme/repo' }],
        status: 'connected',
        enabled: true,
        createdAt: '2026-02-24T10:00:00.000Z',
        updatedAt: '2026-02-24T10:30:00.000Z',
        lastSyncedAt: '2026-02-24T10:40:00.000Z',
      },
    ];

    const slackProgress: SyncProgressSnapshot[] = [
      {
        connectorId: 'connector-slack-primary',
        sourceId: 'C01',
        stage: 'persisting',
        counters: { scanned: 15, changed: 12, upserted: 10 },
        throughputPerSecond: 2.5,
        retry: { attempts: 2, lastRetryAt: '2026-02-24T10:29:00.000Z' },
        updatedAt: '2026-02-24T10:29:01.000Z',
      },
    ];

    const trackerProgress: SyncProgressSnapshot[] = [
      {
        connectorId: 'connector-tracker',
        sourceId: 'acme/repo',
        stage: 'completed',
        counters: { scanned: 20, changed: 3, upserted: 3 },
        throughputPerSecond: 4,
        retry: { attempts: 0, lastRetryAt: null },
        updatedAt: '2026-02-24T10:39:00.000Z',
      },
    ];

    const checkpoints: Record<string, ConnectorCheckpoint[]> = {
      'connector-slack-primary': [
        {
          connectorId: 'connector-slack-primary',
          sourceId: 'C01',
          cursor: { ts: '123.45' },
          updatedAt: '2026-02-24T10:29:02.000Z',
        },
      ],
      'connector-tracker': [
        {
          connectorId: 'connector-tracker',
          sourceId: 'acme/repo',
          cursor: { updatedAt: '2026-02-24T10:38:00.000Z' },
          updatedAt: '2026-02-24T10:39:02.000Z',
        },
      ],
    };

    const payload = buildConnectorHealthPayload({
      connectors,
      progressByConnector: {
        'connector-slack-primary': slackProgress,
        'connector-tracker': trackerProgress,
      },
      checkpointsByConnector: checkpoints,
    });

    expect(payload.summary.dominantStatus).toBe('rate_limited');
    expect(payload.summary.connectorCount).toBe(2);
    expect(payload.summary.lastSuccessfulSyncAt).toBe('2026-02-24T10:40:00.000Z');

    const slack = payload.connectors[0];
    expect(slack.id).toBe('connector-slack-primary');
    expect(slack.counters).toEqual({ scanned: 15, changed: 12, upserted: 10 });
    expect(slack.throughputPerSecond).toBe(2.5);
    expect(slack.recovery.interrupted).toBe(true);
    expect(slack.recovery.canRetry).toBe(true);
    expect(slack.recovery.canResume).toBe(true);
    expect(slack.recovery.blockedByAuth).toBe(false);
    expect(slack.recovery.lastCheckpointAt).toBe('2026-02-24T10:29:02.000Z');
    expect(slack.sources[0].checkpointCursor).toEqual({ ts: '123.45' });

    const tracker = payload.connectors[1];
    expect(tracker.id).toBe('connector-tracker');
    expect(tracker.recovery.interrupted).toBe(false);
    expect(tracker.recovery.canRetry).toBe(false);
  });

  it('marks auth-expired connectors as blocked and reconnect-required', () => {
    const connectors: ConnectorState[] = [
      {
        id: 'connector-tracker',
        provider: 'github',
        sources: [],
        status: 'auth_expired',
        enabled: true,
        createdAt: '2026-02-24T10:00:00.000Z',
        updatedAt: '2026-02-24T10:30:00.000Z',
        lastSyncedAt: '2026-02-24T10:20:00.000Z',
        lastError: 'unauthorized',
      },
    ];

    const payload = buildConnectorHealthPayload({
      connectors,
      progressByConnector: { 'connector-tracker': [] },
      checkpointsByConnector: { 'connector-tracker': [] },
    });

    expect(payload.summary.dominantStatus).toBe('auth_expired');
    expect(payload.connectors[0].recovery.blockedByAuth).toBe(true);
    expect(payload.connectors[0].recovery.canReconnect).toBe(true);
    expect(payload.connectors[0].recovery.canResume).toBe(false);
  });
});
