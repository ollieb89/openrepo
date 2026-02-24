'use client';

import { useState } from 'react';
import Card from '@/components/common/Card';
import {
  reconnectHref,
  statusTrafficLight,
  useSyncStatus,
  type SyncConnectorSnapshot,
  type SyncHealthStatus,
} from '@/lib/hooks/useSyncStatus';

function formatTimestamp(value: string | null): string {
  if (!value) {
    return 'Never';
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleString();
}

function toneClass(status: SyncHealthStatus): string {
  const tone = statusTrafficLight(status);
  if (tone === 'red') {
    return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-200';
  }
  if (tone === 'amber') {
    return 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-200';
  }
  if (tone === 'green') {
    return 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-200';
  }
  if (tone === 'blue') {
    return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-200';
  }
  return 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-200';
}

function statusLabel(status: SyncHealthStatus): string {
  if (status === 'auth_expired') {
    return 'Auth expired';
  }
  if (status === 'rate_limited') {
    return 'Rate limited';
  }
  return status.replace('_', ' ');
}

function RecoveryCard({
  connector,
  onRetry,
  onResume,
  busy,
  actionError,
}: {
  connector: SyncConnectorSnapshot;
  onRetry: () => Promise<void>;
  onResume: () => Promise<void>;
  busy: boolean;
  actionError: string | null;
}) {
  if (connector.recovery.blockedByAuth) {
    return (
      <div className="mt-3 rounded border border-red-300 bg-red-50 p-3 text-xs text-red-800 dark:border-red-800 dark:bg-red-950/30 dark:text-red-200">
        <p className="font-semibold">Authentication expired. Sync is blocked until reconnect.</p>
        <p className="mt-1">
          Last successful sync: {formatTimestamp(connector.lastSyncedAt)}. Last checkpoint: {formatTimestamp(connector.recovery.lastCheckpointAt)}
          {connector.recovery.checkpointSourceId ? ` (${connector.recovery.checkpointSourceId})` : ''}.
        </p>
        <div className="mt-2">
          <a
            href={reconnectHref(connector)}
            className="inline-flex rounded bg-red-600 px-2 py-1 font-medium text-white hover:bg-red-700"
          >
            Reconnect
          </a>
        </div>
      </div>
    );
  }

  if (connector.recovery.interrupted) {
    return (
      <div className="mt-3 rounded border border-amber-300 bg-amber-50 p-3 text-xs text-amber-900 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-200">
        <p className="font-semibold">Sync interrupted.</p>
        <p className="mt-1">
          Resume continues from last checkpoint {formatTimestamp(connector.recovery.lastCheckpointAt)}
          {connector.recovery.checkpointSourceId ? ` in ${connector.recovery.checkpointSourceId}` : ''}, avoiding duplicate replay.
        </p>
        <div className="mt-2 flex flex-wrap gap-2">
          {connector.recovery.canRetry ? (
            <button
              type="button"
              onClick={() => void onRetry()}
              disabled={busy}
              className="rounded bg-amber-600 px-2 py-1 font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
            >
              Retry
            </button>
          ) : null}
          {connector.recovery.canResume ? (
            <button
              type="button"
              onClick={() => void onResume()}
              disabled={busy}
              className="rounded border border-amber-500 px-2 py-1 font-medium text-amber-900 disabled:cursor-not-allowed disabled:opacity-60 dark:text-amber-100"
            >
              Resume now
            </button>
          ) : null}
        </div>
        {actionError ? <p className="mt-2 text-red-700 dark:text-red-300">{actionError}</p> : null}
      </div>
    );
  }

  if (connector.status === 'connected' && connector.lastSyncedAt) {
    return (
      <div className="mt-3 rounded border border-emerald-300 bg-emerald-50 p-3 text-xs text-emerald-900 dark:border-emerald-800 dark:bg-emerald-950/30 dark:text-emerald-200">
        <p className="font-semibold">Last sync completed successfully.</p>
        <p className="mt-1">
          Completed at {formatTimestamp(connector.lastSyncedAt)}. Resume checkpoint available at {formatTimestamp(connector.recovery.lastCheckpointAt)}
          {connector.recovery.checkpointSourceId ? ` (${connector.recovery.checkpointSourceId})` : ''}.
        </p>
      </div>
    );
  }

  return null;
}

function ConnectorProgressCard({
  connector,
  onRetry,
  onResume,
  busy,
  actionError,
}: {
  connector: SyncConnectorSnapshot;
  onRetry: (connector: SyncConnectorSnapshot) => Promise<void>;
  onResume: (connector: SyncConnectorSnapshot) => Promise<void>;
  busy: boolean;
  actionError: string | null;
}) {
  return (
    <div className="rounded-lg border border-gray-200 p-4 dark:border-gray-700">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold capitalize text-gray-900 dark:text-white">{connector.provider}</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">{connector.id}</p>
        </div>
        <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${toneClass(connector.status)}`}>
          {statusLabel(connector.status)}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs text-gray-600 dark:text-gray-300 md:grid-cols-4">
        <p>Stage: <span className="font-medium text-gray-800 dark:text-gray-100">{connector.dominantStage}</span></p>
        <p>Scanned: <span className="font-medium text-gray-800 dark:text-gray-100">{connector.counters.scanned}</span></p>
        <p>Changed: <span className="font-medium text-gray-800 dark:text-gray-100">{connector.counters.changed}</span></p>
        <p>Upserted: <span className="font-medium text-gray-800 dark:text-gray-100">{connector.counters.upserted}</span></p>
        <p>Throughput: <span className="font-medium text-gray-800 dark:text-gray-100">{connector.throughputPerSecond}/s</span></p>
        <p>Retries: <span className="font-medium text-gray-800 dark:text-gray-100">{connector.retry.attempts}</span></p>
        <p>Backoff: <span className="font-medium text-gray-800 dark:text-gray-100">{connector.retry.backoffMs} ms</span></p>
        <p>Last success: <span className="font-medium text-gray-800 dark:text-gray-100">{formatTimestamp(connector.lastSyncedAt)}</span></p>
      </div>

      {connector.sources.length > 0 ? (
        <div className="mt-3 overflow-x-auto">
          <table className="min-w-full text-left text-xs">
            <thead className="text-gray-500 dark:text-gray-400">
              <tr>
                <th className="pr-2">Source</th>
                <th className="pr-2">Stage</th>
                <th className="pr-2">Scanned</th>
                <th className="pr-2">Changed</th>
                <th className="pr-2">Upserted</th>
                <th className="pr-2">TPS</th>
              </tr>
            </thead>
            <tbody className="text-gray-700 dark:text-gray-200">
              {connector.sources.map(source => (
                <tr key={`${connector.id}-${source.sourceId}`}>
                  <td className="pr-2">{source.sourceId}</td>
                  <td className="pr-2">{source.stage}</td>
                  <td className="pr-2">{source.counters.scanned}</td>
                  <td className="pr-2">{source.counters.changed}</td>
                  <td className="pr-2">{source.counters.upserted}</td>
                  <td className="pr-2">{source.throughputPerSecond}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="mt-3 text-xs text-gray-500 dark:text-gray-400">No progress snapshots yet.</p>
      )}

      {connector.lastError ? <p className="mt-3 text-xs text-red-600 dark:text-red-300">Last error: {connector.lastError}</p> : null}

      <RecoveryCard
        connector={connector}
        onRetry={() => onRetry(connector)}
        onResume={() => onResume(connector)}
        busy={busy}
        actionError={actionError}
      />
    </div>
  );
}

export default function SyncDashboard() {
  const { connectors, summary, isLoading, error, refresh, retry, resumeNow } = useSyncStatus();
  const [activeActionId, setActiveActionId] = useState<string | null>(null);
  const [actionErrorById, setActionErrorById] = useState<Record<string, string | null>>({});

  async function onRetry(connector: SyncConnectorSnapshot) {
    setActiveActionId(connector.id);
    setActionErrorById(current => ({ ...current, [connector.id]: null }));
    try {
      await retry(connector);
    } catch (err) {
      setActionErrorById(current => ({
        ...current,
        [connector.id]: err instanceof Error ? err.message : 'Retry failed',
      }));
    } finally {
      setActiveActionId(null);
    }
  }

  async function onResume(connector: SyncConnectorSnapshot) {
    setActiveActionId(connector.id);
    setActionErrorById(current => ({ ...current, [connector.id]: null }));
    try {
      await resumeNow(connector);
    } catch (err) {
      setActionErrorById(current => ({
        ...current,
        [connector.id]: err instanceof Error ? err.message : 'Resume failed',
      }));
    } finally {
      setActiveActionId(null);
    }
  }

  return (
    <Card title="Sync Dashboard" subtitle="Shared connector health and progress across settings and header">
      <div className="space-y-4 p-4">
        <div className="grid grid-cols-2 gap-2 text-xs md:grid-cols-4">
          <div className="rounded border border-gray-200 p-2 dark:border-gray-700">
            <p className="text-gray-500 dark:text-gray-400">Dominant status</p>
            <p className="font-semibold capitalize text-gray-900 dark:text-white">{summary.dominantStatus.replace('_', ' ')}</p>
          </div>
          <div className="rounded border border-gray-200 p-2 dark:border-gray-700">
            <p className="text-gray-500 dark:text-gray-400">Syncing connectors</p>
            <p className="font-semibold text-gray-900 dark:text-white">{summary.syncingCount}</p>
          </div>
          <div className="rounded border border-gray-200 p-2 dark:border-gray-700">
            <p className="text-gray-500 dark:text-gray-400">Connectors with issues</p>
            <p className="font-semibold text-gray-900 dark:text-white">{summary.issueCount}</p>
          </div>
          <div className="rounded border border-gray-200 p-2 dark:border-gray-700">
            <p className="text-gray-500 dark:text-gray-400">Last successful sync</p>
            <p className="font-semibold text-gray-900 dark:text-white">{formatTimestamp(summary.lastSuccessfulSyncAt)}</p>
          </div>
        </div>

        <div>
          <button
            type="button"
            onClick={() => void refresh()}
            className="rounded border border-gray-300 px-3 py-1 text-xs font-medium text-gray-700 dark:border-gray-600 dark:text-gray-200"
          >
            Refresh
          </button>
        </div>

        {isLoading ? <p className="text-sm text-gray-500 dark:text-gray-400">Loading sync dashboard...</p> : null}
        {error ? <p className="text-sm text-red-600 dark:text-red-300">{error.message}</p> : null}

        <div className="space-y-3">
          {connectors.map(connector => (
            <ConnectorProgressCard
              key={connector.id}
              connector={connector}
              onRetry={onRetry}
              onResume={onResume}
              busy={activeActionId === connector.id}
              actionError={actionErrorById[connector.id] || null}
            />
          ))}
          {!isLoading && connectors.length === 0 ? (
            <p className="text-sm text-gray-500 dark:text-gray-400">No connectors found yet.</p>
          ) : null}
        </div>
      </div>
    </Card>
  );
}
