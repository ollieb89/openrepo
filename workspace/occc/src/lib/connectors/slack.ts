import { getConnectorState, upsertConnectorState } from '@/lib/connectors/store';
import {
  registerConnectorSyncAdapter,
  type ConnectorSyncAdapter,
  type SyncBatch,
  type SyncRecord,
} from '@/lib/sync/engine';
import type {
  ConnectorCheckpoint,
  ConnectorCursorPayload,
  ConnectorSourceScope,
  ConnectorState,
} from '@/lib/types/connectors';

export const SLACK_CONNECTOR_ID = 'connector-slack-primary';
export const SLACK_PROVIDER = 'slack';
export const DEFAULT_FIRST_SYNC_WINDOW_DAYS = 30;

export interface SlackWorkspaceMetadata {
  workspaceId: string;
  workspaceName: string;
  teamDomain?: string;
  selectedChannelIds: string[];
  firstSyncWindowDays: number;
  accessToken: string;
  refreshToken?: string;
  tokenExpiresAt?: string;
  scope?: string;
}

interface SlackOAuthTokenResponse {
  ok: boolean;
  error?: string;
  access_token?: string;
  refresh_token?: string;
  expires_in?: number;
  scope?: string;
  team?: {
    id?: string;
    name?: string;
    domain?: string;
  };
}

interface SlackChannel {
  id: string;
  name: string;
  is_archived?: boolean;
}

interface SlackConversationsResponse {
  ok: boolean;
  error?: string;
  channels?: SlackChannel[];
  response_metadata?: {
    next_cursor?: string;
  };
}

interface SlackMessage {
  ts?: string;
  text?: string;
  user?: string;
  subtype?: string;
  thread_ts?: string;
  bot_id?: string;
  [key: string]: unknown;
}

interface SlackHistoryResponse {
  ok: boolean;
  error?: string;
  messages?: SlackMessage[];
  has_more?: boolean;
  response_metadata?: {
    next_cursor?: string;
  };
}

interface SlackApiErrorDetails {
  code: string;
  status?: number;
  message: string;
}

class SlackApiError extends Error {
  status?: number;
  code: string;

  constructor(details: SlackApiErrorDetails) {
    super(details.message);
    this.name = 'SlackApiError';
    this.code = details.code;
    this.status = details.status;
  }
}

function parseNumber(input: unknown, fallback: number): number {
  const n = Number(input);
  return Number.isFinite(n) && n > 0 ? n : fallback;
}

function normalizeWindowDays(input: unknown): number {
  return Math.max(1, Math.min(90, Math.trunc(parseNumber(input, DEFAULT_FIRST_SYNC_WINDOW_DAYS))));
}

function toSlackApiError(status: number, payload: { error?: string } | null, fallbackMessage: string): SlackApiError {
  const code = payload?.error || `http_${status}`;
  const message = payload?.error ? `Slack API error: ${payload.error}` : fallbackMessage;
  return new SlackApiError({ code, status, message });
}

async function slackFetch<T>(input: {
  token: string;
  method: 'GET' | 'POST';
  endpoint: string;
  params?: URLSearchParams;
  body?: Record<string, unknown>;
}): Promise<T> {
  const url = new URL(`https://slack.com/api/${input.endpoint}`);
  if (input.params) {
    url.search = input.params.toString();
  }

  const response = await fetch(url.toString(), {
    method: input.method,
    headers: {
      Authorization: `Bearer ${input.token}`,
      'Content-Type': 'application/json; charset=utf-8',
    },
    body: input.body ? JSON.stringify(input.body) : undefined,
  });

  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    throw toSlackApiError(response.status, payload as { error?: string } | null, 'Slack request failed');
  }

  const parsed = payload as { ok?: boolean; error?: string };
  if (parsed?.ok === false) {
    const errorStatus = parsed.error === 'ratelimited' ? 429 : response.status;
    throw toSlackApiError(errorStatus, parsed, 'Slack request returned ok=false');
  }

  return payload as T;
}

function extractSlackMetadata(connector: ConnectorState): SlackWorkspaceMetadata {
  const metadata = (connector.metadata || {}) as Record<string, unknown>;
  const accessToken = typeof metadata.accessToken === 'string' ? metadata.accessToken : '';
  const workspaceId = typeof metadata.workspaceId === 'string' ? metadata.workspaceId : '';
  const workspaceName = typeof metadata.workspaceName === 'string' ? metadata.workspaceName : 'Slack Workspace';

  if (!accessToken || !workspaceId) {
    throw new SlackApiError({
      code: 'auth_expired',
      status: 401,
      message: 'Slack connector is missing token/workspace metadata. Reconnect Slack.',
    });
  }

  return {
    workspaceId,
    workspaceName,
    teamDomain: typeof metadata.teamDomain === 'string' ? metadata.teamDomain : undefined,
    selectedChannelIds: Array.isArray(metadata.selectedChannelIds)
      ? metadata.selectedChannelIds.filter((value): value is string => typeof value === 'string' && value.length > 0)
      : [],
    firstSyncWindowDays: normalizeWindowDays(metadata.firstSyncWindowDays),
    accessToken,
    refreshToken: typeof metadata.refreshToken === 'string' ? metadata.refreshToken : undefined,
    tokenExpiresAt: typeof metadata.tokenExpiresAt === 'string' ? metadata.tokenExpiresAt : undefined,
    scope: typeof metadata.scope === 'string' ? metadata.scope : undefined,
  };
}

function buildWindowOldestTs(windowDays: number): string {
  const seconds = Math.floor(Date.now() / 1000) - windowDays * 24 * 60 * 60;
  return `${Math.max(seconds, 0)}.000000`;
}

function parseMessageTs(ts: string | undefined): number {
  if (!ts) {
    return 0;
  }

  const numeric = Number(ts);
  return Number.isFinite(numeric) ? numeric : 0;
}

function nextMessageCursor(messages: SlackMessage[], previousTs: string): string {
  const max = messages.reduce((acc, message) => {
    const current = parseMessageTs(message.ts);
    return current > acc ? current : acc;
  }, parseMessageTs(previousTs));

  if (max <= 0) {
    return previousTs;
  }

  return max.toFixed(6);
}

function toSyncRecord(channelId: string, message: SlackMessage): SyncRecord {
  const ts = typeof message.ts === 'string' ? message.ts : `missing-${Math.random()}`;
  return {
    id: `${channelId}:${ts}`,
    payload: {
      connector: 'slack',
      channelId,
      messageTs: ts,
      text: typeof message.text === 'string' ? message.text : '',
      user: typeof message.user === 'string' ? message.user : null,
      subtype: typeof message.subtype === 'string' ? message.subtype : null,
      threadTs: typeof message.thread_ts === 'string' ? message.thread_ts : null,
      botId: typeof message.bot_id === 'string' ? message.bot_id : null,
      raw: message,
    },
  };
}

async function listSlackChannelsInternal(token: string): Promise<ConnectorSourceScope[]> {
  const channels: ConnectorSourceScope[] = [];
  let cursor = '';

  do {
    const params = new URLSearchParams({
      limit: '200',
      types: 'public_channel,private_channel',
      exclude_archived: 'true',
    });

    if (cursor) {
      params.set('cursor', cursor);
    }

    const response = await slackFetch<SlackConversationsResponse>({
      token,
      method: 'GET',
      endpoint: 'conversations.list',
      params,
    });

    for (const channel of response.channels || []) {
      if (channel.is_archived) {
        continue;
      }

      channels.push({
        sourceId: channel.id,
        sourceType: 'channel',
        label: channel.name,
      });
    }

    cursor = response.response_metadata?.next_cursor || '';
  } while (cursor);

  return channels;
}

export async function listSlackChannels(connectorId = SLACK_CONNECTOR_ID): Promise<ConnectorSourceScope[]> {
  const connector = await getConnectorState(connectorId);
  if (!connector) {
    throw new Error('Slack connector is not connected.');
  }

  const metadata = extractSlackMetadata(connector);
  return listSlackChannelsInternal(metadata.accessToken);
}

export async function connectSlackWorkspace(input: {
  code: string;
  redirectUri: string;
  firstSyncWindowDays?: number;
}): Promise<ConnectorState> {
  const clientId = process.env.SLACK_CLIENT_ID;
  const clientSecret = process.env.SLACK_CLIENT_SECRET;

  if (!clientId || !clientSecret) {
    throw new Error('Slack OAuth is not configured. Set SLACK_CLIENT_ID and SLACK_CLIENT_SECRET.');
  }

  const body = new URLSearchParams({
    code: input.code,
    redirect_uri: input.redirectUri,
    client_id: clientId,
    client_secret: clientSecret,
  });

  const response = await fetch('https://slack.com/api/oauth.v2.access', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body,
  });

  const payload = (await response.json()) as SlackOAuthTokenResponse;
  if (!response.ok || !payload.ok || !payload.access_token || !payload.team?.id) {
    const message = payload.error ? `Slack OAuth failed: ${payload.error}` : 'Slack OAuth failed';
    const error = new Error(message) as Error & { status?: number };
    error.status = response.status || 500;
    throw error;
  }

  const expiresIn = Number(payload.expires_in || 0);
  const tokenExpiresAt = expiresIn > 0 ? new Date(Date.now() + expiresIn * 1000).toISOString() : undefined;

  return upsertConnectorState({
    id: SLACK_CONNECTOR_ID,
    provider: SLACK_PROVIDER,
    sources: [],
    status: 'connected',
    enabled: true,
    metadata: {
      workspaceId: payload.team.id,
      workspaceName: payload.team.name || 'Slack Workspace',
      teamDomain: payload.team.domain || null,
      accessToken: payload.access_token,
      refreshToken: payload.refresh_token || null,
      tokenExpiresAt: tokenExpiresAt || null,
      scope: payload.scope || null,
      selectedChannelIds: [],
      firstSyncWindowDays: normalizeWindowDays(input.firstSyncWindowDays),
    },
  });
}

export async function saveSlackChannelSelection(input: {
  selectedChannelIds: string[];
  firstSyncWindowDays?: number;
  connectorId?: string;
}): Promise<ConnectorState> {
  const connectorId = input.connectorId || SLACK_CONNECTOR_ID;
  const connector = await getConnectorState(connectorId);

  if (!connector) {
    throw new Error('Slack connector is not connected.');
  }

  const metadata = extractSlackMetadata(connector);

  return upsertConnectorState({
    ...connector,
    sources: [],
    metadata: {
      ...connector.metadata,
      selectedChannelIds: input.selectedChannelIds,
      firstSyncWindowDays:
        input.firstSyncWindowDays === undefined
          ? metadata.firstSyncWindowDays
          : normalizeWindowDays(input.firstSyncWindowDays),
    },
  });
}

function selectedChannelSources(available: ConnectorSourceScope[], selected: string[]): ConnectorSourceScope[] {
  if (selected.length === 0) {
    return available;
  }

  const lookup = new Set(selected);
  return available.filter(channel => lookup.has(channel.sourceId));
}

function validateFirstWindowRequirement(checkpoint: ConnectorCheckpoint | null, connector: ConnectorState): void {
  if (checkpoint) {
    return;
  }

  const metadata = extractSlackMetadata(connector);
  const window = normalizeWindowDays(metadata.firstSyncWindowDays);
  if (!window || window < 1) {
    throw new Error('First sync window is required before importing Slack messages.');
  }
}

export function createSlackSyncAdapter(): ConnectorSyncAdapter {
  return {
    async listSources(connector) {
      const metadata = extractSlackMetadata(connector);
      const available = await listSlackChannelsInternal(metadata.accessToken);
      return selectedChannelSources(available, metadata.selectedChannelIds);
    },
    async scanChanges({ connector, source, checkpoint }) {
      validateFirstWindowRequirement(checkpoint, connector);

      const metadata = extractSlackMetadata(connector);
      const batches: SyncBatch[] = [];

      let pageCursor = '';
      let messageCursor =
        typeof checkpoint?.cursor?.ts === 'string'
          ? checkpoint.cursor.ts
          : buildWindowOldestTs(metadata.firstSyncWindowDays);

      do {
        const params = new URLSearchParams({
          channel: source.sourceId,
          limit: '200',
          oldest: messageCursor,
          inclusive: 'false',
        });

        if (pageCursor) {
          params.set('cursor', pageCursor);
        }

        const response = await slackFetch<SlackHistoryResponse>({
          token: metadata.accessToken,
          method: 'GET',
          endpoint: 'conversations.history',
          params,
        });

        const messages = (response.messages || []).filter(message => typeof message.ts === 'string');
        const records = messages.map(message => toSyncRecord(source.sourceId, message));

        messageCursor = nextMessageCursor(messages, messageCursor);
        pageCursor = response.response_metadata?.next_cursor || '';

        batches.push({
          records,
          scanned: messages.length,
          changed: records.length,
          nextCursor: {
            ts: messageCursor,
            pageCursor,
            syncedAt: new Date().toISOString(),
          } satisfies ConnectorCursorPayload,
        });
      } while (pageCursor);

      return batches;
    },
    async upsertRecords({ records }) {
      return records.length;
    },
  };
}

let slackAdapterRegistered = false;

export function ensureSlackAdapterRegistered(): void {
  if (slackAdapterRegistered) {
    return;
  }

  registerConnectorSyncAdapter(SLACK_PROVIDER, createSlackSyncAdapter());
  slackAdapterRegistered = true;
}

export async function getSlackConnectorState(): Promise<ConnectorState | null> {
  ensureSlackAdapterRegistered();
  return getConnectorState(SLACK_CONNECTOR_ID);
}

export function slackStatusHint(status: ConnectorState['status']): string {
  if (status === 'rate_limited') {
    return 'Slack API rate-limited. Wait briefly and retry sync.';
  }

  if (status === 'auth_expired') {
    return 'Slack auth expired. Reconnect your workspace.';
  }

  return '';
}
