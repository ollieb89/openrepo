import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import fs from 'fs/promises';
import path from 'path';
import {
  clearConnectorRuntimeStoreForTests,
  getConnectorState,
  upsertConnectorState,
} from '../../src/lib/connectors/store';
import { createGithubTrackerAdapter } from '../../src/lib/connectors/tracker-github';
import { createLinearTrackerAdapter } from '../../src/lib/connectors/tracker-linear';
import { loadCheckpoint } from '../../src/lib/sync/checkpoints';
import { runIncrementalSync } from '../../src/lib/sync/engine';

const testStorePath = path.join(process.cwd(), '.tmp', `tracker-runtime-${process.pid}.json`);

describe('tracker adapters', () => {
  beforeEach(async () => {
    process.env.CONNECTOR_RUNTIME_STORE_PATH = testStorePath;
    await clearConnectorRuntimeStoreForTests();
  });

  afterEach(async () => {
    await clearConnectorRuntimeStoreForTests();
    await fs.rm(path.dirname(testStorePath), { recursive: true, force: true });
    delete process.env.CONNECTOR_RUNTIME_STORE_PATH;
  });

  it('re-ingests GitHub issues changed after the checkpoint based on updatedAt cursor', async () => {
    const persistedIds: string[] = [];
    const githubConnectorId = 'connector-tracker-github';
    const firstRunResponses = [
      [
        {
          id: 101,
          number: 1,
          title: 'Initial title',
          html_url: 'https://github.com/acme/repo/issues/1',
          state: 'open',
          updated_at: '2026-02-24T10:00:00.000Z',
          created_at: '2026-02-24T09:00:00.000Z',
          comments: 0,
          labels: [],
          assignees: [],
        },
      ],
    ];

    const secondRunResponses = [
      [
        {
          id: 101,
          number: 1,
          title: 'Initial title',
          html_url: 'https://github.com/acme/repo/issues/1',
          state: 'open',
          updated_at: '2026-02-24T10:00:00.000Z',
          created_at: '2026-02-24T09:00:00.000Z',
          comments: 0,
          labels: [],
          assignees: [],
        },
        {
          id: 101,
          number: 1,
          title: 'Updated title',
          html_url: 'https://github.com/acme/repo/issues/1',
          state: 'closed',
          updated_at: '2026-02-24T11:00:00.000Z',
          created_at: '2026-02-24T09:00:00.000Z',
          comments: 1,
          labels: [{ name: 'bug' }],
          assignees: [{ login: 'dev1' }],
        },
      ],
    ];

    let run = 0;
    const adapter = createGithubTrackerAdapter({
      fetchImpl: async () => {
        const responses = run === 0 ? firstRunResponses : secondRunResponses;
        const page = responses.shift() || [];
        return new Response(JSON.stringify(page), { status: 200 });
      },
      async persistRecords(records) {
        persistedIds.push(...records.map(record => `${record.id}:${String(record.payload.status)}`));
        return records.length;
      },
    });

    await upsertConnectorState({
      id: githubConnectorId,
      provider: 'github',
      sources: [{ sourceId: 'acme/repo', sourceType: 'github_repo', label: 'acme/repo' }],
      status: 'connected',
      enabled: true,
      metadata: {
        config: {
          owner: 'acme',
          repo: 'repo',
          token: 'ghp_token',
          apiUrl: 'https://mock.github.local',
        },
      },
    });

    await runIncrementalSync({ connectorId: githubConnectorId, adapter });
    run = 1;
    await runIncrementalSync({ connectorId: githubConnectorId, adapter });

    expect(persistedIds).toEqual([
      'github:acme/repo#1:open',
      'github:acme/repo#1:closed',
    ]);

    const checkpoint = await loadCheckpoint(githubConnectorId, 'acme/repo');
    expect(checkpoint?.cursor).toEqual({
      updatedAt: '2026-02-24T11:00:00.000Z',
      recordId: 'github:acme/repo#1',
    });
  });

  it('paginates Linear updates and advances cursor by updatedAt + id', async () => {
    const persisted: string[] = [];

    const linearConnectorId = 'connector-tracker-linear';
    const responses: Array<{ nodes: Array<Record<string, unknown>>; hasNextPage: boolean; endCursor: string | null }> = [
      {
        nodes: [
          {
            id: 'lin_1',
            identifier: 'ENG-101',
            title: 'Bug fix',
            url: 'https://linear.app/acme/issue/ENG-101',
            createdAt: '2026-02-24T08:00:00.000Z',
            updatedAt: '2026-02-24T10:00:00.000Z',
            priority: 1,
            state: { name: 'Todo' },
            assignee: null,
            team: { id: 'team_1', key: 'ENG', name: 'Engineering' },
            labels: { nodes: [] },
          },
        ],
        hasNextPage: true,
        endCursor: 'cursor_1',
      },
      {
        nodes: [
          {
            id: 'lin_2',
            identifier: 'ENG-102',
            title: 'Status changed',
            url: 'https://linear.app/acme/issue/ENG-102',
            createdAt: '2026-02-24T08:30:00.000Z',
            updatedAt: '2026-02-24T11:00:00.000Z',
            priority: 2,
            state: { name: 'Done' },
            assignee: { id: 'usr_1', name: 'Alex' },
            team: { id: 'team_1', key: 'ENG', name: 'Engineering' },
            labels: { nodes: [{ id: 'lbl_1', name: 'sync' }] },
          },
        ],
        hasNextPage: false,
        endCursor: null,
      },
    ];

    const adapter = createLinearTrackerAdapter({
      fetchImpl: async () => {
        const page = responses.shift() || { nodes: [], hasNextPage: false, endCursor: null };
        return new Response(
          JSON.stringify({
            data: {
              issues: {
                nodes: page.nodes,
                pageInfo: {
                  hasNextPage: page.hasNextPage,
                  endCursor: page.endCursor,
                },
              },
            },
          }),
          { status: 200 }
        );
      },
      async persistRecords(records) {
        persisted.push(...records.map(record => record.id));
        return records.length;
      },
    });

    await upsertConnectorState({
      id: linearConnectorId,
      provider: 'linear',
      sources: [{ sourceId: 'team_1', sourceType: 'linear_team', label: 'team_1' }],
      status: 'connected',
      enabled: true,
      metadata: {
        config: {
          teamId: 'team_1',
          token: 'lin_api_token',
          apiUrl: 'https://mock.linear.local/graphql',
        },
      },
    });

    await runIncrementalSync({ connectorId: linearConnectorId, adapter });

    expect(persisted).toEqual(['linear:lin_1', 'linear:lin_2']);

    const checkpoint = await loadCheckpoint(linearConnectorId, 'team_1');
    expect(checkpoint?.cursor).toEqual({
      updatedAt: '2026-02-24T11:00:00.000Z',
      recordId: 'linear:lin_2',
    });
  });

  it('maps tracker provider auth and rate limit responses to shared health states', async () => {
    const connectorId = 'connector-tracker-health';

    await upsertConnectorState({
      id: connectorId,
      provider: 'github',
      sources: [{ sourceId: 'acme/repo', sourceType: 'github_repo', label: 'acme/repo' }],
      status: 'connected',
      enabled: true,
      metadata: {
        config: {
          owner: 'acme',
          repo: 'repo',
          token: 'ghp_token',
          apiUrl: 'https://mock.github.local',
        },
      },
    });

    const unauthorizedAdapter = createGithubTrackerAdapter({
      fetchImpl: async () => new Response(JSON.stringify({ message: 'unauthorized' }), { status: 401 }),
    });

    await expect(runIncrementalSync({ connectorId, adapter: unauthorizedAdapter })).rejects.toThrow();
    const afterUnauthorized = await getConnectorState(connectorId);
    expect(afterUnauthorized?.status).toBe('auth_expired');

    const rateLimitedAdapter = createGithubTrackerAdapter({
      fetchImpl: async () => new Response(JSON.stringify({ message: 'rate limited' }), { status: 429 }),
    });

    await expect(runIncrementalSync({ connectorId, adapter: rateLimitedAdapter })).rejects.toThrow();
    const afterRateLimit = await getConnectorState(connectorId);
    expect(afterRateLimit?.status).toBe('rate_limited');
  });
});
