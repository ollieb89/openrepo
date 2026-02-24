import type {
  ConnectorCheckpoint,
  ConnectorHealthStatus,
  ConnectorProgressCounters,
  ConnectorState,
  SyncProgressSnapshot,
  SyncStage,
} from '@/lib/types/connectors';
import { sortHealthStatuses } from '@/lib/sync/health';

export const HEALTH_STATUS_PRIORITY: ConnectorHealthStatus[] = [
  'auth_expired',
  'error',
  'rate_limited',
  'syncing',
  'connected',
  'disconnected',
];

export interface ConnectorSourceHealthSnapshot {
  sourceId: string;
  stage: SyncStage;
  counters: ConnectorProgressCounters;
  throughputPerSecond: number;
  retry: {
    attempts: number;
    lastRetryAt: string | null;
    backoffMs: number;
  };
  checkpointUpdatedAt: string | null;
  checkpointCursor: Record<string, unknown> | null;
  updatedAt: string;
}

export interface ConnectorHealthSnapshot {
  id: string;
  provider: string;
  status: ConnectorHealthStatus;
  statusPriority: number;
  enabled: boolean;
  lastSyncedAt: string | null;
  lastError: string | null;
  dominantStage: SyncStage;
  counters: ConnectorProgressCounters;
  throughputPerSecond: number;
  retry: {
    attempts: number;
    lastRetryAt: string | null;
    backoffMs: number;
  };
  sources: ConnectorSourceHealthSnapshot[];
  recovery: {
    interrupted: boolean;
    blockedByAuth: boolean;
    canRetry: boolean;
    canRetryAction: boolean; // Renamed to avoid name clash if needed
    canResume: boolean;
    canReconnect: boolean;
    lastCheckpointAt: string | null;
    checkpointSourceId: string | null;
  };
}

export interface ConnectorHealthPayload {
  generatedAt: string;
  summary: {
    dominantStatus: ConnectorHealthStatus;
    syncingCount: number;
    issueCount: number;
    connectorCount: number;
    lastSuccessfulSyncAt: string | null;
  };
  connectors: ConnectorHealthSnapshot[];
}

function buildCheckpointIndex(checkpoints: ConnectorCheckpoint[]): Record<string, ConnectorCheckpoint> {
  return checkpoints.reduce<Record<string, ConnectorCheckpoint>>((acc, checkpoint) => {
    acc[checkpoint.sourceId] = checkpoint;
    return acc;
  }, {});
}

function stagePriority(stage: SyncStage): number {
  switch (stage) {
    case 'failed':
      return 7;
    case 'saving_checkpoint':
      return 6;
    case 'persisting':
      return 5;
    case 'scanning':
      return 4;
    case 'loading_checkpoint':
      return 3;
    case 'initializing':
      return 2;
    case 'completed':
      return 1;
    default:
      return 0;
  }
}

function computeBackoffMs(attempts: number): number {
  if (attempts <= 0) {
    return 0;
  }

  return Math.min(30000, Math.pow(2, attempts) * 500);
}

function reduceCounters(progress: SyncProgressSnapshot[]): ConnectorProgressCounters {
  return progress.reduce(
    (acc, entry) => ({
      scanned: acc.scanned + entry.counters.scanned,
      changed: acc.changed + entry.counters.changed,
      upserted: acc.upserted + entry.counters.upserted,
    }),
    { scanned: 0, changed: 0, upserted: 0 }
  );
}

function pickDominantStage(progress: SyncProgressSnapshot[]): SyncStage {
  if (progress.length === 0) {
    return 'idle';
  }

  return [...progress].sort((a, b) => stagePriority(b.stage) - stagePriority(a.stage))[0].stage;
}

function maxIsoDate(values: Array<string | null | undefined>): string | null {
  const valid = values
    .filter((value): value is string => typeof value === 'string')
    .map(value => {
      const timestamp = Date.parse(value);
      return Number.isNaN(timestamp) ? null : timestamp;
    })
    .filter((value): value is number => value != null);

  if (valid.length === 0) {
    return null;
  }

  return new Date(Math.max(...valid)).toISOString();
}

export function buildConnectorHealthPayload(input: {
  connectors: ConnectorState[];
  progressByConnector: Record<string, SyncProgressSnapshot[]>;
  checkpointsByConnector: Record<string, ConnectorCheckpoint[]>;
}): ConnectorHealthPayload {
  const connectors = input.connectors.map(connector => {
    const progressEntries = input.progressByConnector[connector.id] || [];
    const checkpoints = input.checkpointsByConnector[connector.id] || [];
    const checkpointIndex = buildCheckpointIndex(checkpoints);

    const sourceSnapshots: ConnectorSourceHealthSnapshot[] = progressEntries
      .map(entry => {
        const checkpoint = checkpointIndex[entry.sourceId] || null;
        return {
          sourceId: entry.sourceId,
          stage: entry.stage,
          counters: entry.counters,
          throughputPerSecond: entry.throughputPerSecond,
          retry: {
            attempts: entry.retry.attempts,
            lastRetryAt: entry.retry.lastRetryAt,
            backoffMs: computeBackoffMs(entry.retry.attempts),
          },
          checkpointUpdatedAt: checkpoint?.updatedAt || null,
          checkpointCursor: (checkpoint?.cursor as Record<string, unknown>) || null,
          updatedAt: entry.updatedAt,
        };
      })
      .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));

    const counters = reduceCounters(progressEntries);
    const throughputPerSecond = Number(
      sourceSnapshots.reduce((acc, source) => acc + source.throughputPerSecond, 0).toFixed(2)
    );

    const totalRetryAttempts = sourceSnapshots.reduce((acc, source) => acc + source.retry.attempts, 0);
    const lastRetryAt = maxIsoDate(sourceSnapshots.map(source => source.retry.lastRetryAt));
    const retryBackoffMs = sourceSnapshots.reduce((acc, source) => Math.max(acc, source.retry.backoffMs), 0);

    const checkpointSource = checkpoints
      .slice()
      .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))[0];

    const interrupted = connector.status === 'error' || connector.status === 'rate_limited';

    return {
      id: connector.id,
      provider: connector.provider,
      status: connector.status,
      statusPriority: HEALTH_STATUS_PRIORITY.length - HEALTH_STATUS_PRIORITY.indexOf(connector.status),
      enabled: connector.enabled,
      lastSyncedAt: connector.lastSyncedAt || null,
      lastError: connector.lastError || null,
      dominantStage: pickDominantStage(progressEntries),
      counters,
      throughputPerSecond,
      retry: {
        attempts: totalRetryAttempts,
        lastRetryAt,
        backoffMs: retryBackoffMs,
      },
      sources: sourceSnapshots,
      recovery: {
        interrupted,
        blockedByAuth: connector.status === 'auth_expired',
        canRetry: connector.status === 'error' || connector.status === 'rate_limited',
        canResume: connector.status !== 'auth_expired' && (interrupted || connector.status === 'syncing'),
        canReconnect: connector.status === 'auth_expired',
        lastCheckpointAt: checkpointSource?.updatedAt || null,
        checkpointSourceId: checkpointSource?.sourceId || null,
      },
    } as ConnectorHealthSnapshot;
  });

  const dominantStatus = sortHealthStatuses(connectors.map(connector => connector.status))[0] || 'disconnected';

  return {
    generatedAt: new Date().toISOString(),
    summary: {
      dominantStatus,
      syncingCount: connectors.filter(connector => connector.status === 'syncing').length,
      issueCount: connectors.filter(
        connector => connector.status === 'auth_expired' || connector.status === 'error' || connector.status === 'rate_limited'
      ).length,
      connectorCount: connectors.length,
      lastSuccessfulSyncAt: maxIsoDate(connectors.map(connector => connector.lastSyncedAt)),
    },
    connectors: connectors.sort((a, b) => b.statusPriority - a.statusPriority),
  };
}
