import type { ConnectorHealthStatus } from '@/lib/types/connectors';

const HEALTH_PRIORITY: Record<ConnectorHealthStatus, number> = {
  auth_expired: 6,
  error: 5,
  rate_limited: 4,
  syncing: 3,
  connected: 2,
  disconnected: 1,
};

export function classifyConnectorHealth(input: {
  httpStatus?: number | null;
  error?: unknown;
  isSyncing?: boolean;
  isConnected?: boolean;
}): ConnectorHealthStatus {
  if (input.httpStatus === 401 || input.httpStatus === 403) {
    return 'auth_expired';
  }

  if (input.httpStatus === 429) {
    return 'rate_limited';
  }

  if (input.error) {
    return 'error';
  }

  if (input.isSyncing) {
    return 'syncing';
  }

  if (input.isConnected) {
    return 'connected';
  }

  return 'disconnected';
}

export function getHealthPriority(status: ConnectorHealthStatus): number {
  return HEALTH_PRIORITY[status];
}

export function sortHealthStatuses(statuses: ConnectorHealthStatus[]): ConnectorHealthStatus[] {
  return [...statuses].sort((a, b) => HEALTH_PRIORITY[b] - HEALTH_PRIORITY[a]);
}

export function pickDominantHealthStatus(statuses: ConnectorHealthStatus[]): ConnectorHealthStatus {
  if (statuses.length === 0) {
    return 'disconnected';
  }

  return sortHealthStatuses(statuses)[0];
}
