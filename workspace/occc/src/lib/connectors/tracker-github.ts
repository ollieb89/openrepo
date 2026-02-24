import type { ConnectorCheckpoint, ConnectorState } from '@/lib/types/connectors';
import type { SyncBatch, SyncRecord } from '@/lib/sync/engine';
import {
  buildTrackerSources,
  readTrackerConnectorConfig,
  requestTrackerJson,
  TRACKER_PROVIDER_GITHUB,
  type GithubTrackerConfig,
  type TrackerSyncAdapter,
} from '@/lib/connectors/tracker';

interface GitHubIssue {
  id: number;
  number: number;
  title: string;
  html_url: string;
  state: string;
  updated_at: string;
  created_at: string;
  comments: number;
  labels?: Array<{ name: string }>;
  assignees?: Array<{ login: string }>;
  pull_request?: unknown;
}

interface GitHubCursor {
  updatedAt: string;
  recordId: string;
}

function readCursor(checkpoint: ConnectorCheckpoint | null): GitHubCursor | null {
  const updatedAt = checkpoint?.cursor.updatedAt;
  const recordId = checkpoint?.cursor.recordId;
  if (typeof updatedAt !== 'string' || typeof recordId !== 'string') {
    return null;
  }
  return { updatedAt, recordId };
}

function isAfterCursor(recordUpdatedAt: string, recordId: string, cursor: GitHubCursor | null): boolean {
  if (!cursor) {
    return true;
  }

  if (recordUpdatedAt > cursor.updatedAt) {
    return true;
  }

  if (recordUpdatedAt === cursor.updatedAt) {
    return recordId > cursor.recordId;
  }

  return false;
}

function sourceIdFor(config: GithubTrackerConfig): string {
  return `${config.owner}/${config.repo}`;
}

function issueToSyncRecord(issue: GitHubIssue, sourceId: string): SyncRecord {
  const recordId = `github:${sourceId}#${issue.number}`;

  return {
    id: recordId,
    payload: {
      provider: 'github',
      sourceId,
      externalId: String(issue.number),
      title: issue.title,
      status: issue.state,
      url: issue.html_url,
      updatedAt: issue.updated_at,
      createdAt: issue.created_at,
      metadata: {
        comments: issue.comments,
        labels: issue.labels?.map(label => label.name) || [],
        assignees: issue.assignees?.map(assignee => assignee.login) || [],
      },
    },
  };
}

async function fetchIssuePage(input: {
  fetchImpl?: typeof fetch;
  config: GithubTrackerConfig;
  since?: string;
  page: number;
  perPage: number;
}): Promise<GitHubIssue[]> {
  const baseUrl = input.config.apiUrl || 'https://api.github.com';
  const url = new URL(`${baseUrl.replace(/\/$/, '')}/repos/${input.config.owner}/${input.config.repo}/issues`);
  url.searchParams.set('state', 'all');
  url.searchParams.set('sort', 'updated');
  url.searchParams.set('direction', 'asc');
  url.searchParams.set('per_page', String(input.perPage));
  url.searchParams.set('page', String(input.page));

  if (input.since) {
    url.searchParams.set('since', input.since);
  }

  return requestTrackerJson<GitHubIssue[]>({
    fetchImpl: input.fetchImpl,
    provider: TRACKER_PROVIDER_GITHUB,
    url: url.toString(),
    init: {
      headers: {
        Authorization: `Bearer ${input.config.token}`,
        Accept: 'application/vnd.github+json',
      },
    },
  });
}

export function createGithubTrackerAdapter(input?: {
  fetchImpl?: typeof fetch;
  persistRecords?: (records: SyncRecord[], connector: ConnectorState) => Promise<number>;
}): TrackerSyncAdapter {
  return {
    async listSources(connector) {
      const trackerConfig = readTrackerConnectorConfig(connector);
      return buildTrackerSources(trackerConfig);
    },

    async *scanChanges({ connector, checkpoint }) {
      const trackerConfig = readTrackerConnectorConfig(connector);
      if (trackerConfig.provider !== TRACKER_PROVIDER_GITHUB) {
        throw new Error('GitHub adapter received non-GitHub connector');
      }

      const config = trackerConfig.config;
      const sourceId = sourceIdFor(config);
      const cursor = readCursor(checkpoint);
      const since = cursor?.updatedAt;

      const perPage = 100;
      let page = 1;

      while (true) {
        const items = await fetchIssuePage({
          fetchImpl: input?.fetchImpl,
          config,
          since,
          page,
          perPage,
        });

        const filtered = items
          .filter(item => !item.pull_request)
          .map(item => issueToSyncRecord(item, sourceId))
          .filter(item => {
            const updatedAt = String(item.payload.updatedAt);
            return isAfterCursor(updatedAt, item.id, cursor);
          })
          .sort((a, b) => {
            const aUpdated = String(a.payload.updatedAt);
            const bUpdated = String(b.payload.updatedAt);
            if (aUpdated !== bUpdated) {
              return aUpdated.localeCompare(bUpdated);
            }
            return a.id.localeCompare(b.id);
          });

        if (filtered.length > 0) {
          const last = filtered[filtered.length - 1];
          const batch: SyncBatch = {
            records: filtered,
            scanned: items.length,
            changed: filtered.length,
            nextCursor: {
              updatedAt: last.payload.updatedAt,
              recordId: last.id,
            },
          };

          yield batch;
        }

        if (items.length < perPage) {
          break;
        }

        page += 1;
      }
    },

    async upsertRecords({ connector, records }) {
      if (input?.persistRecords) {
        return input.persistRecords(records, connector);
      }
      return records.length;
    },
  };
}
