'use client';

import { useMemo, useState } from 'react';
import Card from '@/components/common/Card';
import { usePrivacy } from '@/lib/hooks/usePrivacy';

interface PrivacyCenterProps {
  projectId: string | null;
}

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

export default function PrivacyCenter({ projectId }: PrivacyCenterProps) {
  const {
    settings,
    events,
    filters,
    setFilters,
    error,
    isLoadingSettings,
    isLoadingEvents,
    setRemoteConsent,
    revokeConsent,
  } = usePrivacy(projectId);

  const [isSaving, setIsSaving] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const remoteEnabled = settings?.remoteInferenceEnabled === true;
  const updatedAtLabel = settings?.updatedAt ? formatDate(settings.updatedAt) : 'Never';

  const eventsSummary = useMemo(() => {
    const remote = events.filter(event => event.mode === 'remote').length;
    const local = events.filter(event => event.mode === 'local').length;
    return { remote, local };
  }, [events]);

  async function onToggleConsent(enabled: boolean) {
    setIsSaving(true);
    setActionError(null);
    try {
      await setRemoteConsent(enabled);
    } catch {
      setActionError('Could not save privacy setting.');
    } finally {
      setIsSaving(false);
    }
  }

  async function onRevoke() {
    setIsSaving(true);
    setActionError(null);
    try {
      await revokeConsent();
    } catch {
      setActionError('Could not revoke consent.');
    } finally {
      setIsSaving(false);
    }
  }

  if (!projectId) {
    return (
      <Card className="p-6" title="Privacy Center" subtitle="Project-scoped remote inference controls">
        <p className="text-sm text-gray-500 dark:text-gray-400">Select a project to manage privacy settings.</p>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card
        className="p-6"
        title="Privacy Center"
        subtitle="Control remote inference consent for this project"
      >
        <div className="space-y-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-medium text-gray-900 dark:text-white">Remote inference consent</p>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Allow remote inference only when local confidence is below threshold.
              </p>
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">Last updated: {updatedAtLabel}</p>
            </div>

            <label className="inline-flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
              <input
                type="checkbox"
                checked={remoteEnabled}
                onChange={event => onToggleConsent(event.target.checked)}
                disabled={isSaving || isLoadingSettings}
                className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              {remoteEnabled ? 'Enabled' : 'Disabled'}
            </label>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={onRevoke}
              disabled={isSaving || isLoadingSettings}
              className="rounded-md border border-red-200 bg-red-50 px-3 py-1.5 text-sm font-medium text-red-700 hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-60"
            >
              Revoke consent
            </button>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              One click revoke sets remote inference to disabled.
            </p>
          </div>

          {actionError && <p className="text-sm text-red-600">{actionError}</p>}
          {error && <p className="text-sm text-red-600">Failed to load privacy data.</p>}
        </div>
      </Card>

      <Card
        className="p-6"
        title="Inference Audit Log"
        subtitle="Filter remote/local usage by reason, connector, and time range"
      >
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-5">
            <label className="text-xs text-gray-600 dark:text-gray-300">
              Mode
              <select
                value={filters.mode}
                onChange={event => setFilters(prev => ({ ...prev, mode: event.target.value as typeof prev.mode }))}
                className="mt-1 block w-full rounded-md border border-gray-300 bg-white px-2 py-1.5 text-sm text-gray-900"
              >
                <option value="all">All</option>
                <option value="local">Local</option>
                <option value="remote">Remote</option>
              </select>
            </label>

            <label className="text-xs text-gray-600 dark:text-gray-300">
              Reason contains
              <input
                value={filters.reason}
                onChange={event => setFilters(prev => ({ ...prev, reason: event.target.value }))}
                className="mt-1 block w-full rounded-md border border-gray-300 bg-white px-2 py-1.5 text-sm text-gray-900"
                placeholder="consent"
              />
            </label>

            <label className="text-xs text-gray-600 dark:text-gray-300">
              Connector
              <input
                value={filters.connector}
                onChange={event => setFilters(prev => ({ ...prev, connector: event.target.value }))}
                className="mt-1 block w-full rounded-md border border-gray-300 bg-white px-2 py-1.5 text-sm text-gray-900"
                placeholder="inference"
              />
            </label>

            <label className="text-xs text-gray-600 dark:text-gray-300">
              From
              <input
                type="datetime-local"
                value={filters.from}
                onChange={event => setFilters(prev => ({ ...prev, from: event.target.value }))}
                className="mt-1 block w-full rounded-md border border-gray-300 bg-white px-2 py-1.5 text-sm text-gray-900"
              />
            </label>

            <label className="text-xs text-gray-600 dark:text-gray-300">
              To
              <input
                type="datetime-local"
                value={filters.to}
                onChange={event => setFilters(prev => ({ ...prev, to: event.target.value }))}
                className="mt-1 block w-full rounded-md border border-gray-300 bg-white px-2 py-1.5 text-sm text-gray-900"
              />
            </label>
          </div>

          <div className="text-xs text-gray-500 dark:text-gray-400">
            {events.length} events ({eventsSummary.remote} remote / {eventsSummary.local} local)
          </div>

          {isLoadingEvents ? (
            <p className="text-sm text-gray-500 dark:text-gray-400">Loading events...</p>
          ) : events.length === 0 ? (
            <p className="text-sm text-gray-500 dark:text-gray-400">No matching privacy events.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200 dark:border-gray-700 text-left text-xs text-gray-500">
                    <th className="py-2 pr-3">Time</th>
                    <th className="py-2 pr-3">Mode</th>
                    <th className="py-2 pr-3">Reason</th>
                    <th className="py-2 pr-3">Connector</th>
                  </tr>
                </thead>
                <tbody>
                  {events.map(event => (
                    <tr key={event.id} className="border-b border-gray-100 dark:border-gray-800">
                      <td className="py-2 pr-3 text-gray-600 dark:text-gray-300">{formatDate(event.createdAt)}</td>
                      <td className="py-2 pr-3">
                        <span
                          className={`inline-flex rounded px-1.5 py-0.5 text-xs font-medium ${
                            event.mode === 'remote'
                              ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200'
                              : 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200'
                          }`}
                        >
                          {event.mode}
                        </span>
                      </td>
                      <td className="py-2 pr-3 text-gray-700 dark:text-gray-200">{event.reason}</td>
                      <td className="py-2 pr-3 text-gray-600 dark:text-gray-300">{event.connector}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}
