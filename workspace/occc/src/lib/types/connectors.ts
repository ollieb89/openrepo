export type ConnectorHealthStatus =
  | 'connected'
  | 'syncing'
  | 'rate_limited'
  | 'auth_expired'
  | 'error'
  | 'disconnected';

export interface ConnectorSourceScope {
  sourceId: string;
  sourceType: string;
  label?: string;
}

export interface ConnectorCursorPayload {
  [key: string]: unknown;
}

export interface ConnectorCheckpoint {
  connectorId: string;
  sourceId: string;
  cursor: ConnectorCursorPayload;
  updatedAt: string;
}

export interface ConnectorProgressCounters {
  scanned: number;
  changed: number;
  upserted: number;
}

export type SyncStage =
  | 'idle'
  | 'initializing'
  | 'loading_checkpoint'
  | 'scanning'
  | 'persisting'
  | 'saving_checkpoint'
  | 'completed'
  | 'failed';

export interface ConnectorRetryMetadata {
  attempts: number;
  lastRetryAt: string | null;
}

export interface SyncProgressSnapshot {
  connectorId: string;
  sourceId: string;
  stage: SyncStage;
  counters: ConnectorProgressCounters;
  throughputPerSecond: number;
  retry: ConnectorRetryMetadata;
  updatedAt: string;
}

export interface ConnectorState {
  id: string;
  provider: string;
  sources: ConnectorSourceScope[];
  status: ConnectorHealthStatus;
  enabled: boolean;
  createdAt: string;
  updatedAt: string;
  lastSyncedAt?: string;
  lastError?: string;
  metadata?: Record<string, unknown>;
}
