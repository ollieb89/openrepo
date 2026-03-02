'use client';

import useSWR from 'swr';
import { apiPath } from '@/lib/api-client';

export type SyncHealthStatus = 'auth_expired' | 'error' | 'rate_limited' | 'syncing' | 'connected' | 'disconnected';
export type SyncStage =
  | 'idle'
  | 'initializing'
  | 'loading_checkpoint'
  | 'scanning'
  | 'persisting'
  | 'saving_checkpoint'
  | 'completed'
  | 'failed';

export interface SyncSourceSnapshot {
  sourceId: string;
  stage: SyncStage;
  counters: {
    scanned: number;
    changed: number;
    upserted: number;
  };
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

export interface SyncConnectorSnapshot {
  id: string;
  provider: string;
  status: SyncHealthStatus;
  statusPriority: number;
  enabled: boolean;
  lastSyncedAt: string | null;
  lastError: string | null;
  dominantStage: SyncStage;
  counters: {
    scanned: number;
    changed: number;
    upserted: number;
  };
  throughputPerSecond: number;
  retry: {
    attempts: number;
    lastRetryAt: string | null;
    backoffMs: number;
  };
  sources: SyncSourceSnapshot[];
  recovery: {
    interrupted: boolean;
    blockedByAuth: boolean;
    canRetry: boolean;
    canResume: boolean;
    canReconnect: boolean;
    lastCheckpointAt: string | null;
    checkpointSourceId: string | null;
  };
}

export interface SyncHealthPayload {
  generatedAt: string;
  summary: {
    dominantStatus: SyncHealthStatus;
    syncingCount: number;
    issueCount: number;
    connectorCount: number;
    lastSuccessfulSyncAt: string | null;
  };
  connectors: SyncConnectorSnapshot[];
}

export const SYNC_STATUS_PRIORITY: SyncHealthStatus[] = [
  'auth_expired',
  'error',
  'rate_limited',
  'syncing',
  'connected',
  'disconnected',
];

const fetcher = async (url: string) => {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch sync status (${response.status})`);
  }
  return (await response.json()) as SyncHealthPayload;
};

export function sortStatusesByPriority(statuses: SyncHealthStatus[]): SyncHealthStatus[] {
  return [...statuses].sort(
    (left, right) => SYNC_STATUS_PRIORITY.indexOf(left) - SYNC_STATUS_PRIORITY.indexOf(right)
  );
}

export function statusTrafficLight(status: SyncHealthStatus): 'red' | 'amber' | 'green' | 'blue' | 'gray' {
  if (status === 'auth_expired' || status === 'error') {
    return 'red';
  }
  if (status === 'rate_limited') {
    return 'amber';
  }
  if (status === 'connected') {
    return 'green';
  }
  if (status === 'syncing') {
    return 'blue';
  }
  return 'gray';
}

export function resolveSyncEndpoint(connector: Pick<SyncConnectorSnapshot, 'id' | 'provider'>): string {
  if (connector.id === 'connector-slack-primary' || connector.provider === 'slack') {
    return apiPath('/api/connectors/slack/sync');
  }
  if (connector.id === 'connector-tracker' || connector.provider === 'github' || connector.provider === 'linear') {
    return apiPath('/api/connectors/tracker/sync');
  }
  return apiPath(`/api/connectors/${encodeURIComponent(connector.id)}/sync`);
}

export function reconnectHref(connector: Pick<SyncConnectorSnapshot, 'id' | 'provider'>): string {
  if (connector.id === 'connector-slack-primary' || connector.provider === 'slack') {
    return '/settings/connectors#slack-connector';
  }
  if (connector.id === 'connector-tracker' || connector.provider === 'github' || connector.provider === 'linear') {
    return '/settings/connectors#tracker-connector';
  }
  return '/settings/connectors';
}

async function triggerConnectorSync(connector: Pick<SyncConnectorSnapshot, 'id' | 'provider'>): Promise<void> {
  const response = await fetch(resolveSyncEndpoint(connector), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ connectorId: connector.id }),
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok || payload.ok === false) {
    throw new Error(payload.error || `Failed to sync ${connector.id}`);
  }
}

export function useSyncStatus() {
  const syncSWR = useSWR<SyncHealthPayload>(apiPath('/api/connectors/health'), fetcher, {
    refreshInterval: 3000,
    revalidateOnFocus: false,
  });

  async function retry(connector: SyncConnectorSnapshot): Promise<void> {
    if (connector.status === 'auth_expired') {
      throw new Error('Reconnect is required before retrying this sync.');
    }

    await triggerConnectorSync(connector);
    await syncSWR.mutate();
  }

  async function resumeNow(connector: SyncConnectorSnapshot): Promise<void> {
    if (connector.status === 'auth_expired') {
      throw new Error('Authentication expired. Reconnect before resuming.');
    }

    await triggerConnectorSync(connector);
    await syncSWR.mutate();
  }

  return {
    data: syncSWR.data,
    connectors: syncSWR.data?.connectors || [],
    summary: syncSWR.data?.summary || {
      dominantStatus: 'disconnected' as const,
      syncingCount: 0,
      issueCount: 0,
      connectorCount: 0,
      lastSuccessfulSyncAt: null,
    },
    isLoading: syncSWR.isLoading,
    error: syncSWR.error as Error | undefined,
    retry,
    resumeNow,
    refresh: async () => {
      await syncSWR.mutate();
    },
  };
}
