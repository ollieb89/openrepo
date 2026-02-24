import type { ConnectorSyncAdapter, SyncRecord } from '@/lib/sync/engine';
import type { ConnectorSourceScope, ConnectorState } from '@/lib/types/connectors';

export const TRACKER_PROVIDER_GITHUB = 'github';
export const TRACKER_PROVIDER_LINEAR = 'linear';

export type TrackerProvider = typeof TRACKER_PROVIDER_GITHUB | typeof TRACKER_PROVIDER_LINEAR;

export interface GithubTrackerConfig {
  owner: string;
  repo: string;
  token: string;
  apiUrl?: string;
}

export interface LinearTrackerConfig {
  token: string;
  teamId?: string;
  apiUrl?: string;
}

export type TrackerConnectorConfig =
  | {
      provider: typeof TRACKER_PROVIDER_GITHUB;
      config: GithubTrackerConfig;
    }
  | {
      provider: typeof TRACKER_PROVIDER_LINEAR;
      config: LinearTrackerConfig;
    };

export interface TrackerIssuePayload {
  provider: TrackerProvider;
  sourceId: string;
  externalId: string;
  title: string;
  status: string;
  url: string;
  updatedAt: string;
  createdAt: string;
  metadata?: Record<string, unknown>;
}

export type TrackerSyncRecord = SyncRecord & { payload: TrackerIssuePayload };
export type TrackerSyncAdapter = ConnectorSyncAdapter;

export class TrackerRequestError extends Error {
  status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.name = 'TrackerRequestError';
    this.status = status;
  }
}

function asObject(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error('Tracker metadata must be an object');
  }
  return value as Record<string, unknown>;
}

function readRequiredString(input: Record<string, unknown>, key: string): string {
  const value = input[key];
  if (typeof value !== 'string' || value.trim() === '') {
    throw new Error(`Tracker config missing required string: ${key}`);
  }
  return value.trim();
}

function readOptionalString(input: Record<string, unknown>, key: string): string | undefined {
  const value = input[key];
  if (value == null) {
    return undefined;
  }
  if (typeof value !== 'string' || value.trim() === '') {
    throw new Error(`Tracker config invalid optional string: ${key}`);
  }
  return value.trim();
}

export function assertTrackerProvider(provider: string): TrackerProvider {
  if (provider === TRACKER_PROVIDER_GITHUB || provider === TRACKER_PROVIDER_LINEAR) {
    return provider;
  }

  throw new Error(`Unsupported tracker provider: ${provider}`);
}

export function readTrackerConnectorConfig(connector: ConnectorState): TrackerConnectorConfig {
  const provider = assertTrackerProvider(connector.provider);
  const metadata = asObject(connector.metadata ?? {});
  const config = asObject(metadata.config ?? {});

  if (provider === TRACKER_PROVIDER_GITHUB) {
    return {
      provider,
      config: {
        owner: readRequiredString(config, 'owner'),
        repo: readRequiredString(config, 'repo'),
        token: readRequiredString(config, 'token'),
        apiUrl: readOptionalString(config, 'apiUrl'),
      },
    };
  }

  return {
    provider,
    config: {
      token: readRequiredString(config, 'token'),
      teamId: readOptionalString(config, 'teamId'),
      apiUrl: readOptionalString(config, 'apiUrl'),
    },
  };
}

export function buildTrackerSources(config: TrackerConnectorConfig): ConnectorSourceScope[] {
  if (config.provider === TRACKER_PROVIDER_GITHUB) {
    const repo = `${config.config.owner}/${config.config.repo}`;
    return [{ sourceId: repo, sourceType: 'github_repo', label: repo }];
  }

  const sourceId = config.config.teamId || 'linear-workspace';
  return [{ sourceId, sourceType: 'linear_team', label: sourceId }];
}

export async function requestTrackerJson<T>(input: {
  fetchImpl?: typeof fetch;
  url: string;
  init?: RequestInit;
  provider: TrackerProvider;
}): Promise<T> {
  const fetcher = input.fetchImpl || fetch;
  const response = await fetcher(input.url, input.init);

  if (!response.ok) {
    throw new TrackerRequestError(
      `${input.provider} request failed with status ${response.status}`,
      response.status
    );
  }

  return (await response.json()) as T;
}
