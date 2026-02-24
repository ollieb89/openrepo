'use client';

import { useEffect, useMemo, useState } from 'react';
import Card from '@/components/common/Card';
import { useConnectorStatus } from '@/lib/hooks/useConnectorStatus';

function toInputDate(value: string | null): string {
  if (!value) {
    return 'Never';
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString();
}

function statusBadgeClass(status: string): string {
  if (status === 'connected') {
    return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300';
  }

  if (status === 'syncing') {
    return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300';
  }

  if (status === 'rate_limited') {
    return 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300';
  }

  if (status === 'auth_expired' || status === 'error') {
    return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300';
  }

  return 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300';
}

export default function SlackConnectorCard() {
  const {
    status,
    channels,
    selectedChannelIds,
    firstSyncWindowDays,
    lastSyncedAt,
    hint,
    isLoading,
    isMutating,
    error,
    connectSlack,
    saveChannelScope,
    syncNow,
  } = useConnectorStatus();

  const [oauthCode, setOauthCode] = useState('');
  const [redirectUri, setRedirectUri] = useState('http://localhost:6987/settings/connectors');
  const [windowDays, setWindowDays] = useState(firstSyncWindowDays);
  const [selectedIds, setSelectedIds] = useState<string[]>(selectedChannelIds);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionInfo, setActionInfo] = useState<string | null>(null);

  const orderedChannels = useMemo(
    () => [...channels].sort((a, b) => (a.label || a.sourceId).localeCompare(b.label || b.sourceId)),
    [channels]
  );

  useEffect(() => {
    setWindowDays(firstSyncWindowDays);
  }, [firstSyncWindowDays]);

  useEffect(() => {
    setSelectedIds(selectedChannelIds);
  }, [selectedChannelIds]);

  function toggleChannel(channelId: string) {
    setSelectedIds(current =>
      current.includes(channelId) ? current.filter(id => id !== channelId) : [...current, channelId]
    );
  }

  async function onConnect() {
    setActionError(null);
    setActionInfo(null);
    try {
      await connectSlack({ code: oauthCode.trim(), redirectUri: redirectUri.trim(), firstSyncWindowDays: windowDays });
      setActionInfo('Slack workspace connected. Select channels and save scope.');
      setOauthCode('');
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Unable to connect Slack');
    }
  }

  async function onSaveScope() {
    setActionError(null);
    setActionInfo(null);
    try {
      await saveChannelScope({ selectedChannelIds: selectedIds, firstSyncWindowDays: windowDays });
      setActionInfo('Slack channel scope saved.');
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Unable to save channel scope');
    }
  }

  async function onSyncNow() {
    setActionError(null);
    setActionInfo(null);
    try {
      await syncNow(windowDays);
      setActionInfo('Slack sync completed.');
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Slack sync failed');
    }
  }

  return (
    <Card
      title="Slack"
      subtitle="Connect one workspace, choose sync channels, and run incremental syncs"
      className="max-w-4xl"
    >
      <div className="space-y-4 p-4">
        <div className="flex flex-wrap items-center gap-3 text-sm">
          <span className={`inline-flex rounded-full px-2 py-0.5 font-medium ${statusBadgeClass(status)}`}>
            {status}
          </span>
          <span className="text-gray-600 dark:text-gray-300">Last sync: {toInputDate(lastSyncedAt)}</span>
        </div>

        <p className="text-sm text-gray-600 dark:text-gray-300">{hint}</p>

        {error ? <p className="text-sm text-red-600 dark:text-red-300">{String(error.message || error)}</p> : null}
        {actionError ? <p className="text-sm text-red-600 dark:text-red-300">{actionError}</p> : null}
        {actionInfo ? <p className="text-sm text-green-700 dark:text-green-300">{actionInfo}</p> : null}

        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <label className="flex flex-col gap-1 text-sm text-gray-700 dark:text-gray-300">
            OAuth code
            <input
              value={oauthCode}
              onChange={event => setOauthCode(event.target.value)}
              className="rounded-md border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-900"
              placeholder="Paste Slack OAuth code"
            />
          </label>

          <label className="flex flex-col gap-1 text-sm text-gray-700 dark:text-gray-300 md:col-span-2">
            Redirect URI
            <input
              value={redirectUri}
              onChange={event => setRedirectUri(event.target.value)}
              className="rounded-md border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-900"
              placeholder="https://your-app/settings/connectors"
            />
          </label>

          <label className="flex flex-col gap-1 text-sm text-gray-700 dark:text-gray-300">
            First sync window (days)
            <input
              min={1}
              max={90}
              type="number"
              value={windowDays}
              onChange={event => setWindowDays(Math.min(90, Math.max(1, Number(event.target.value) || 30)))}
              className="rounded-md border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-900"
            />
          </label>
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={onConnect}
            disabled={isMutating || isLoading || oauthCode.trim().length === 0 || redirectUri.trim().length === 0}
            className="rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
          >
            Connect Workspace
          </button>
          <button
            type="button"
            onClick={onSaveScope}
            disabled={isMutating || isLoading}
            className="rounded-md border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:text-gray-200"
          >
            Save Channel Scope
          </button>
          <button
            type="button"
            onClick={onSyncNow}
            disabled={isMutating || isLoading}
            className="rounded-md bg-emerald-600 px-3 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
          >
            Sync now
          </button>
        </div>

        <div className="space-y-2">
          <p className="text-sm font-medium text-gray-800 dark:text-gray-200">Channels in sync scope</p>
          <div className="grid max-h-56 grid-cols-1 gap-2 overflow-auto pr-1 md:grid-cols-2">
            {orderedChannels.length === 0 ? (
              <p className="text-sm text-gray-500 dark:text-gray-400">No channels loaded yet. Connect workspace first.</p>
            ) : (
              orderedChannels.map(channel => {
                const checked = selectedIds.includes(channel.sourceId);
                return (
                  <label
                    key={channel.sourceId}
                    className="flex items-center gap-2 rounded border border-gray-200 px-3 py-2 text-sm dark:border-gray-700"
                  >
                    <input checked={checked} onChange={() => toggleChannel(channel.sourceId)} type="checkbox" />
                    <span>#{channel.label || channel.sourceId}</span>
                  </label>
                );
              })
            )}
          </div>
        </div>
      </div>
    </Card>
  );
}
