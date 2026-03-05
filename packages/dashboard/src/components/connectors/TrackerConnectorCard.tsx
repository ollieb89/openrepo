'use client';

import { useEffect, useMemo, useState } from 'react';
import Card from '@/components/common/Card';
import type { ConnectorHealthStatus } from '@/lib/types/connectors';
import { apiJson, apiFetch } from '@/lib/api-client';

type TrackerProvider = 'github' | 'linear';

interface TrackerConnectorResponse {
  connector: {
    id: string;
    provider: TrackerProvider;
    status: ConnectorHealthStatus;
    enabled: boolean;
    lastSyncedAt?: string;
    lastError?: string;
    metadata?: {
      config?: Record<string, unknown>;
    };
  } | null;
  reauthRequired: boolean;
}

const HEALTH_LABELS: Record<ConnectorHealthStatus, string> = {
  connected: 'Connected',
  syncing: 'Syncing',
  rate_limited: 'Rate Limited',
  auth_expired: 'Authentication Expired',
  error: 'Error',
  disconnected: 'Disconnected',
};

const HEALTH_STYLES: Record<ConnectorHealthStatus, string> = {
  connected: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  syncing: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
  rate_limited: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300',
  auth_expired: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
  error: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
  disconnected: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200',
};

function formatTimestamp(value?: string): string {
  if (!value) {
    return 'Never';
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return 'Never';
  }

  return parsed.toLocaleString();
}

function readString(value: unknown): string {
  return typeof value === 'string' ? value : '';
}

export default function TrackerConnectorCard() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [provider, setProvider] = useState<TrackerProvider>('github');
  const [githubOwner, setGithubOwner] = useState('');
  const [githubRepo, setGithubRepo] = useState('');
  const [githubToken, setGithubToken] = useState('');
  const [linearToken, setLinearToken] = useState('');
  const [linearTeamId, setLinearTeamId] = useState('');
  const [snapshot, setSnapshot] = useState<TrackerConnectorResponse | null>(null);

  const status = snapshot?.connector?.status || 'disconnected';
  const isAuthExpired = status === 'auth_expired';

  async function loadState() {
    setLoading(true);
    setError(null);

    try {
      const data = await apiJson<TrackerConnectorResponse>('/api/connectors/tracker');
      setSnapshot(data);

      if (data.connector) {
        setProvider(data.connector.provider);
        const config = data.connector.metadata?.config || {};

        setGithubOwner(readString(config.owner));
        setGithubRepo(readString(config.repo));
        setGithubToken(readString(config.token));
        setLinearToken(readString(config.token));
        setLinearTeamId(readString(config.teamId));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load tracker connector state');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadState();
  }, []);

  const providerConfig = useMemo(() => {
    if (provider === 'github') {
      return {
        owner: githubOwner,
        repo: githubRepo,
        token: githubToken,
      };
    }

    return {
      token: linearToken,
      teamId: linearTeamId || undefined,
    };
  }, [githubOwner, githubRepo, githubToken, linearToken, linearTeamId, provider]);

  async function saveConnector() {
    setSaving(true);
    setError(null);

    try {
      const body = await apiJson<any>('/api/connectors/tracker', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          provider,
          config: providerConfig,
          enabled: true,
        }),
      });
      if (body.ok === false) {
        throw new Error(body.error || 'Failed to configure tracker connector');
      }

      await loadState();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save tracker connector');
    } finally {
      setSaving(false);
    }
  }

  async function runSync() {
    setSyncing(true);
    setError(null);

    try {
      const body = await apiJson<any>('/api/connectors/tracker/sync', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({}),
      });
      if (body.ok === false) {
        throw new Error(body.error || 'Failed to sync tracker connector');
      }

      await loadState();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to run tracker sync');
    } finally {
      setSyncing(false);
    }
  }

  const actionLabel = isAuthExpired ? 'Reconnect' : 'Connect';

  return (
    <Card
      title="Tracker Connector"
      subtitle="Connect GitHub Issues or Linear and run incremental metadata sync"
      action={
        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${HEALTH_STYLES[status]}`}>
          {HEALTH_LABELS[status]}
        </span>
      }
    >
      <div className="space-y-4 p-4">
        {loading ? <p className="text-sm text-gray-500 dark:text-gray-400">Loading tracker connector...</p> : null}

        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Provider</label>
          <div className="flex gap-4">
            <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
              <input
                type="radio"
                name="tracker-provider"
                value="github"
                checked={provider === 'github'}
                onChange={() => setProvider('github')}
              />
              GitHub Issues
            </label>
            <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
              <input
                type="radio"
                name="tracker-provider"
                value="linear"
                checked={provider === 'linear'}
                onChange={() => setProvider('linear')}
              />
              Linear
            </label>
          </div>
        </div>

        {provider === 'github' ? (
          <div className="grid gap-3 md:grid-cols-2">
            <label className="space-y-1 text-sm text-gray-700 dark:text-gray-300">
              <span>Owner</span>
              <input
                className="w-full rounded border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-900"
                value={githubOwner}
                onChange={event => setGithubOwner(event.target.value)}
                placeholder="acme"
              />
            </label>
            <label className="space-y-1 text-sm text-gray-700 dark:text-gray-300">
              <span>Repository</span>
              <input
                className="w-full rounded border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-900"
                value={githubRepo}
                onChange={event => setGithubRepo(event.target.value)}
                placeholder="product"
              />
            </label>
            <label className="space-y-1 text-sm text-gray-700 dark:text-gray-300 md:col-span-2">
              <span>Access Token</span>
              <input
                className="w-full rounded border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-900"
                value={githubToken}
                onChange={event => setGithubToken(event.target.value)}
                placeholder="ghp_..."
                type="password"
              />
            </label>
          </div>
        ) : (
          <div className="grid gap-3 md:grid-cols-2">
            <label className="space-y-1 text-sm text-gray-700 dark:text-gray-300 md:col-span-2">
              <span>API Token</span>
              <input
                className="w-full rounded border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-900"
                value={linearToken}
                onChange={event => setLinearToken(event.target.value)}
                placeholder="lin_api_..."
                type="password"
              />
            </label>
            <label className="space-y-1 text-sm text-gray-700 dark:text-gray-300">
              <span>Team ID (optional)</span>
              <input
                className="w-full rounded border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-900"
                value={linearTeamId}
                onChange={event => setLinearTeamId(event.target.value)}
                placeholder="team_123"
              />
            </label>
          </div>
        )}

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={saveConnector}
            disabled={saving}
            className="rounded bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {saving ? 'Saving...' : actionLabel}
          </button>
          <button
            type="button"
            onClick={runSync}
            disabled={syncing || !snapshot?.connector}
            className="rounded border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-60 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700"
          >
            {syncing ? 'Syncing...' : 'Sync Now'}
          </button>
          <button
            type="button"
            onClick={() => void loadState()}
            disabled={loading}
            className="rounded border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-60 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700"
          >
            Refresh
          </button>
        </div>

        <div className="space-y-1 text-sm text-gray-600 dark:text-gray-300">
          <p>Last Successful Sync: {formatTimestamp(snapshot?.connector?.lastSyncedAt)}</p>
          {isAuthExpired ? (
            <p className="text-red-600 dark:text-red-300">
              Authentication expired. Reconnect with a fresh token to resume syncing.
            </p>
          ) : null}
          {snapshot?.connector?.lastError ? (
            <p className="text-red-600 dark:text-red-300">Last Error: {snapshot.connector.lastError}</p>
          ) : null}
          {error ? <p className="text-red-600 dark:text-red-300">{error}</p> : null}
        </div>
      </div>
    </Card>
  );
}
