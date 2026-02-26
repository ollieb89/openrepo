import type { ConnectorCheckpoint, ConnectorState } from '@/lib/types/connectors';
import type { SyncBatch, SyncRecord } from '@/lib/sync/engine';
import {
  buildTrackerSources,
  readTrackerConnectorConfig,
  requestTrackerJson,
  TRACKER_PROVIDER_LINEAR,
  type LinearTrackerConfig,
  type TrackerSyncAdapter,
} from '@/lib/connectors/tracker';

interface LinearIssue {
  id: string;
  identifier: string;
  title: string;
  url: string;
  createdAt: string;
  updatedAt: string;
  priority?: number | null;
  state?: { name?: string | null } | null;
  assignee?: { id: string; name: string } | null;
  team?: { id: string; key?: string | null; name?: string | null } | null;
  labels?: { nodes?: Array<{ id: string; name: string }> } | null;
}

interface LinearGraphResponse {
  data?: {
    issues?: {
      nodes: LinearIssue[];
      pageInfo: {
        hasNextPage: boolean;
        endCursor: string | null;
      };
    };
  };
}

interface LinearCursor {
  updatedAt: string;
  recordId: string;
}

function readCursor(checkpoint: ConnectorCheckpoint | null): LinearCursor | null {
  const updatedAt = checkpoint?.cursor.updatedAt;
  const recordId = checkpoint?.cursor.recordId;
  if (typeof updatedAt !== 'string' || typeof recordId !== 'string') {
    return null;
  }
  return { updatedAt, recordId };
}

function isAfterCursor(recordUpdatedAt: string, recordId: string, cursor: LinearCursor | null): boolean {
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

function sourceIdFor(config: LinearTrackerConfig): string {
  return config.teamId || 'linear-workspace';
}

function issueToSyncRecord(issue: LinearIssue, sourceId: string): SyncRecord {
  const recordId = `linear:${issue.id}`;

  return {
    id: recordId,
    payload: {
      provider: 'linear',
      sourceId,
      externalId: issue.identifier,
      title: issue.title,
      status: issue.state?.name || 'unknown',
      url: issue.url,
      updatedAt: issue.updatedAt,
      createdAt: issue.createdAt,
      metadata: {
        priority: issue.priority,
        team: issue.team || null,
        assignee: issue.assignee || null,
        labels: issue.labels?.nodes || [],
      },
    },
  };
}

async function fetchIssuePage(input: {
  fetchImpl?: typeof fetch;
  config: LinearTrackerConfig;
  updatedAfter?: string;
  after?: string | null;
}): Promise<{ issues: LinearIssue[]; hasNextPage: boolean; endCursor: string | null }> {
  const endpoint = input.config.apiUrl || 'https://api.linear.app/graphql';
  const query = `
    query TrackerIssues($first: Int!, $after: String, $filter: IssueFilter) {
      issues(first: $first, after: $after, filter: $filter, orderBy: updatedAt) {
        nodes {
          id
          identifier
          title
          url
          createdAt
          updatedAt
          priority
          state { name }
          assignee { id name }
          team { id key name }
          labels { nodes { id name } }
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
    }
  `;

  const filter: Record<string, unknown> = {};
  if (input.updatedAfter) {
    filter.updatedAt = { gte: input.updatedAfter };
  }
  if (input.config.teamId) {
    filter.team = { id: { eq: input.config.teamId } };
  }

  const payload = {
    query,
    variables: {
      first: 100,
      after: input.after || null,
      filter,
    },
  };

  const response = await requestTrackerJson<LinearGraphResponse>({
    fetchImpl: input.fetchImpl,
    provider: TRACKER_PROVIDER_LINEAR,
    url: endpoint,
    init: {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: input.config.token,
      },
      body: JSON.stringify(payload),
    },
  });

  const issues = response.data?.issues?.nodes || [];
  const pageInfo = response.data?.issues?.pageInfo;

  return {
    issues,
    hasNextPage: pageInfo?.hasNextPage || false,
    endCursor: pageInfo?.endCursor || null,
  };
}

export function createLinearTrackerAdapter(input?: {
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
      if (trackerConfig.provider !== TRACKER_PROVIDER_LINEAR) {
        throw new Error('Linear adapter received non-Linear connector');
      }

      const config = trackerConfig.config;
      const sourceId = sourceIdFor(config);
      const cursor = readCursor(checkpoint);
      const updatedAfter = cursor?.updatedAt;
      let after: string | null = null;

      while (true) {
        const page = await fetchIssuePage({
          fetchImpl: input?.fetchImpl,
          config,
          updatedAfter,
          after,
        });

        const filtered = page.issues
          .map(issue => issueToSyncRecord(issue, sourceId))
          .filter(record => {
            const updatedAt = String(record.payload.updatedAt);
            return isAfterCursor(updatedAt, record.id, cursor);
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
            scanned: page.issues.length,
            changed: filtered.length,
            nextCursor: {
              updatedAt: last.payload.updatedAt,
              recordId: last.id,
            },
          };

          yield batch;
        }

        if (!page.hasNextPage) {
          break;
        }

        after = page.endCursor;
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
