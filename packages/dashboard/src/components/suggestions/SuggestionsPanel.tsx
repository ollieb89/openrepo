'use client';

import { useState } from 'react';
import useSWR from 'swr';
import type { Suggestion, SuggestionsData } from '@/lib/types/suggestions';
import SuggestionCard from './SuggestionCard';
import DismissedTab from './DismissedTab';

const fetcher = (url: string) => fetch(url).then(r => r.json());

function useSuggestions(projectId: string | null) {
  const key = projectId ? `/api/suggestions?project=${projectId}` : null;
  const { data, error, isLoading, mutate } = useSWR<SuggestionsData>(key, fetcher, {
    revalidateOnFocus: false,
  });
  return { data, isLoading, error, mutate };
}

function formatRelative(isoTimestamp: string): string {
  try {
    const date = new Date(isoTimestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  } catch {
    return isoTimestamp;
  }
}

interface SuggestionsPanelProps {
  projectId: string | null;
}

export default function SuggestionsPanel({ projectId }: SuggestionsPanelProps) {
  const { data, isLoading, error, mutate } = useSuggestions(projectId);
  const [activeTab, setActiveTab] = useState<'pending' | 'dismissed'>('pending');
  const [isRunning, setIsRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);

  async function handleRunAnalysis() {
    if (!projectId || isRunning) return;
    setIsRunning(true);
    setRunError(null);
    try {
      await fetch(`/api/suggestions?project=${projectId}`, { method: 'POST' });
      await mutate();
    } catch {
      setRunError('Analysis failed. Check that memU is running.');
    } finally {
      setIsRunning(false);
    }
  }

  async function handleAccept(suggestion: Suggestion) {
    const res = await fetch(`/api/suggestions/${suggestion.id}/action`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'accept', project: projectId, diff_text: suggestion.diff_text }),
    });
    if (res.ok) {
      await mutate();
    }
  }

  async function handleReject(suggestion: Suggestion, reason: string) {
    await fetch(`/api/suggestions/${suggestion.id}/action`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'reject', project: projectId, rejection_reason: reason }),
    });
    await mutate();
  }

  const pendingSuggestions = (data?.suggestions ?? [])
    .filter(s => s.status === 'pending')
    .sort((a, b) => b.evidence_count - a.evidence_count);

  const dismissedSuggestions = (data?.suggestions ?? []).filter(s => s.status === 'rejected');

  return (
    <div className="space-y-4">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-gray-900 dark:text-white">SOUL Suggestions</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Review and approve pattern-based SOUL amendments
        </p>
      </div>

      {/* Last run + Run analysis */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Last run:{' '}
          {data?.last_run ? (
            <span className="text-gray-700 dark:text-gray-300">{formatRelative(data.last_run)}</span>
          ) : (
            <span className="text-gray-400 dark:text-gray-500">Never</span>
          )}
        </p>
        <div className="flex items-center gap-2">
          {runError && (
            <span className="text-sm text-red-600 dark:text-red-400">{runError}</span>
          )}
          <button
            type="button"
            onClick={handleRunAnalysis}
            disabled={!projectId || isRunning}
            className="flex items-center gap-2 rounded-md bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed px-3 py-1.5 text-sm font-medium text-white transition-colors"
          >
            {isRunning && (
              <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            )}
            {isRunning ? 'Analyzing...' : 'Run analysis'}
          </button>
        </div>
      </div>

      {/* Tab bar */}
      <div className="flex border-b border-gray-200 dark:border-gray-700">
        <button
          type="button"
          onClick={() => setActiveTab('pending')}
          className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'pending'
              ? 'border-blue-600 text-blue-600 dark:text-blue-400 dark:border-blue-400'
              : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'
          }`}
        >
          Pending
          {pendingSuggestions.length > 0 && (
            <span className="inline-flex items-center justify-center rounded-full bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 text-xs font-bold min-w-[18px] h-[18px] px-1">
              {pendingSuggestions.length}
            </span>
          )}
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('dismissed')}
          className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'dismissed'
              ? 'border-blue-600 text-blue-600 dark:text-blue-400 dark:border-blue-400'
              : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'
          }`}
        >
          Dismissed
        </button>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="flex items-center justify-center py-16 text-gray-400 dark:text-gray-500">
          <svg className="animate-spin w-6 h-6 mr-2" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          Loading suggestions...
        </div>
      )}

      {/* Error state */}
      {!isLoading && error && (
        <div className="rounded-md border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 px-4 py-3 text-sm text-red-700 dark:text-red-300">
          Failed to load suggestions. Please try again.
        </div>
      )}

      {/* Tab content */}
      {!isLoading && !error && (
        <>
          {activeTab === 'pending' && (
            <>
              {pendingSuggestions.length === 0 ? (
                <div className="text-center py-12 text-gray-400 dark:text-gray-500">
                  <p>Last run: {data?.last_run ? formatRelative(data.last_run) : 'Never'}</p>
                  <p className="mt-1">No patterns met the threshold.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {pendingSuggestions.map(suggestion => (
                    <SuggestionCard
                      key={suggestion.id}
                      suggestion={suggestion}
                      onAccept={handleAccept}
                      onReject={handleReject}
                    />
                  ))}
                </div>
              )}
            </>
          )}

          {activeTab === 'dismissed' && (
            <DismissedTab suggestions={dismissedSuggestions} />
          )}
        </>
      )}
    </div>
  );
}
