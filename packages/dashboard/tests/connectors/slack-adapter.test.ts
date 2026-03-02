import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import fs from 'fs/promises';
import path from 'path';
import { clearConnectorRuntimeStoreForTests, upsertConnectorState } from '../../src/lib/connectors/store';
import {
  createSlackSyncAdapter,
  DEFAULT_FIRST_SYNC_WINDOW_DAYS,
  SLACK_CONNECTOR_ID,
  SLACK_PROVIDER,
} from '../../src/lib/connectors/slack';
import type { ConnectorCheckpoint } from '../../src/lib/types/connectors';

const testStorePath = path.join(process.cwd(), '.tmp', `slack-adapter-${process.pid}.json`);

describe('slack adapter', () => {
  const originalFetch = global.fetch;

  beforeEach(async () => {
    process.env.CONNECTOR_RUNTIME_STORE_PATH = testStorePath;
    await clearConnectorRuntimeStoreForTests();
  });

  afterEach(async () => {
    await clearConnectorRuntimeStoreForTests();
    await fs.rm(path.dirname(testStorePath), { recursive: true, force: true });
    delete process.env.CONNECTOR_RUNTIME_STORE_PATH;
    global.fetch = originalFetch;
  });

  it('uses selected channels and first-sync default window when no checkpoint exists', async () => {
    await upsertConnectorState({
      id: SLACK_CONNECTOR_ID,
      provider: SLACK_PROVIDER,
      sources: [],
      status: 'connected',
      enabled: true,
      metadata: {
        workspaceId: 'T01',
        workspaceName: 'Workspace',
        accessToken: 'xoxb-token',
        selectedChannelIds: ['C1'],
      },
    });

    const fetchMock = vi.fn(async (input: string | URL) => {
      const url = new URL(input.toString());
      if (url.pathname.endsWith('/conversations.list')) {
        return new Response(
          JSON.stringify({
            ok: true,
            channels: [
              { id: 'C1', name: 'eng' },
              { id: 'C2', name: 'ops' },
            ],
            response_metadata: { next_cursor: '' },
          }),
          { status: 200 }
        );
      }

      if (url.pathname.endsWith('/conversations.history')) {
        expect(url.searchParams.get('channel')).toBe('C1');
        const oldest = url.searchParams.get('oldest');
        expect(typeof oldest).toBe('string');
        const oldestNum = Number(oldest);
        const nowSec = Date.now() / 1000;
        expect(oldestNum).toBeGreaterThan(nowSec - (DEFAULT_FIRST_SYNC_WINDOW_DAYS + 1) * 24 * 60 * 60);

        const ts1 = `${Math.floor(oldestNum) + 1}.000001`;
        const ts2 = `${Math.floor(oldestNum) + 2}.000002`;

        return new Response(
          JSON.stringify({
            ok: true,
            messages: [
              { ts: ts1, text: 'one' },
              { ts: ts2, text: 'two' },
            ],
            response_metadata: { next_cursor: '' },
          }),
          { status: 200 }
        );
      }

      return new Response(JSON.stringify({ ok: false, error: 'unknown_method' }), { status: 404 });
    });

    global.fetch = fetchMock as typeof fetch;

    const adapter = createSlackSyncAdapter();
    const connector = {
      id: SLACK_CONNECTOR_ID,
      provider: SLACK_PROVIDER,
      sources: [],
      status: 'connected',
      enabled: true,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      metadata: {
        workspaceId: 'T01',
        workspaceName: 'Workspace',
        accessToken: 'xoxb-token',
        selectedChannelIds: ['C1'],
      },
    };

    const sources = await adapter.listSources(connector);
    expect(sources.map(source => source.sourceId)).toEqual(['C1']);

    const scanBatches = await adapter.scanChanges({
      connector,
      source: sources[0],
      checkpoint: null,
    });

    const batches = [...(scanBatches as Array<{ records: Array<{ id: string }>; nextCursor: { ts: string } }>)] ;
    expect(batches).toHaveLength(1);
    expect(batches[0].records).toHaveLength(2);
    expect(Number(batches[0].nextCursor.ts)).toBeGreaterThan(0);
    expect(fetchMock).toHaveBeenCalled();
  });

  it('resumes incremental history from checkpoint cursor ts', async () => {
    const fetchMock = vi.fn(async (input: string | URL) => {
      const url = new URL(input.toString());
      if (url.pathname.endsWith('/conversations.history')) {
        expect(url.searchParams.get('oldest')).toBe('1710000999.000001');
        return new Response(
          JSON.stringify({
            ok: true,
            messages: [{ ts: '1710001000.000100', text: 'delta' }],
            response_metadata: { next_cursor: '' },
          }),
          { status: 200 }
        );
      }

      if (url.pathname.endsWith('/conversations.list')) {
        return new Response(
          JSON.stringify({
            ok: true,
            channels: [{ id: 'C9', name: 'updates' }],
            response_metadata: { next_cursor: '' },
          }),
          { status: 200 }
        );
      }

      return new Response(JSON.stringify({ ok: false, error: 'bad' }), { status: 500 });
    });

    global.fetch = fetchMock as typeof fetch;

    const adapter = createSlackSyncAdapter();
    const connector = {
      id: SLACK_CONNECTOR_ID,
      provider: SLACK_PROVIDER,
      sources: [],
      status: 'connected',
      enabled: true,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      metadata: {
        workspaceId: 'T01',
        workspaceName: 'Workspace',
        accessToken: 'xoxb-token',
        selectedChannelIds: ['C9'],
        firstSyncWindowDays: 7,
      },
    };

    const checkpoint: ConnectorCheckpoint = {
      connectorId: SLACK_CONNECTOR_ID,
      sourceId: 'C9',
      cursor: { ts: '1710000999.000001' },
      updatedAt: new Date().toISOString(),
    };

    const sources = await adapter.listSources(connector);
    const scanBatches = await adapter.scanChanges({
      connector,
      source: sources[0],
      checkpoint,
    });

    const batches = [...(scanBatches as Array<{ records: Array<{ id: string }>; nextCursor: { ts: string } }>)] ;
    expect(batches).toHaveLength(1);
    expect(batches[0].records[0].id).toBe('C9:1710001000.000100');
    expect(batches[0].nextCursor.ts).toBe('1710001000.000100');
  });
});
