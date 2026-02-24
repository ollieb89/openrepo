'use client';

import { useMemo } from 'react';
import { statusTrafficLight, useSyncStatus } from '@/lib/hooks/useSyncStatus';

function toneClass(tone: 'red' | 'amber' | 'green' | 'blue' | 'gray'): string {
  if (tone === 'red') {
    return 'bg-red-500';
  }
  if (tone === 'amber') {
    return 'bg-amber-500';
  }
  if (tone === 'green') {
    return 'bg-emerald-500';
  }
  if (tone === 'blue') {
    return 'bg-blue-500';
  }
  return 'bg-gray-400';
}

function labelForStatus(status: string): string {
  if (status === 'auth_expired') {
    return 'Auth Expired';
  }
  if (status === 'rate_limited') {
    return 'Rate Limited';
  }
  if (status === 'syncing') {
    return 'Syncing';
  }
  if (status === 'connected') {
    return 'Connected';
  }
  if (status === 'error') {
    return 'Error';
  }
  return 'Disconnected';
}

export default function HeaderSyncStatus() {
  const { summary, isLoading } = useSyncStatus();

  const tone = useMemo(() => statusTrafficLight(summary.dominantStatus), [summary.dominantStatus]);

  return (
    <div className="flex items-center gap-2 rounded-md border border-gray-200 px-2 py-1 text-xs dark:border-gray-600">
      <span className={`h-2.5 w-2.5 rounded-full ${toneClass(tone)}`} />
      <span className="text-gray-600 dark:text-gray-300">
        {isLoading ? 'Sync: loading' : `Sync: ${labelForStatus(summary.dominantStatus)}`}
      </span>
      {!isLoading ? (
        <span className="text-gray-500 dark:text-gray-400">
          {summary.syncingCount > 0 ? `${summary.syncingCount} active` : `${summary.issueCount} issues`}
        </span>
      ) : null}
    </div>
  );
}
