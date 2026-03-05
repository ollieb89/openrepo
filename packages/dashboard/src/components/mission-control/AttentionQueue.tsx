'use client';

import { useState } from 'react';
import Link from 'next/link';
import { apiFetch } from '@/lib/api-client';
import { useProject } from '@/context/ProjectContext';
import { useEscalatingTasks } from '@/lib/hooks/useEscalatingTasks';
import { useDecisions } from '@/lib/hooks/useDecisions';
import { useSuggestions } from '@/lib/hooks/useSuggestions';
import type { Decision } from '@/lib/types/decisions';

type ItemKind = 'escalation' | 'decision' | 'suggestion';

interface AttentionItem {
  id: string;
  kind: ItemKind;
  label: string;
}

const MAX_ITEMS = 5;

export default function AttentionQueue() {
  const { projectId } = useProject();
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());
  const [acting, setActing] = useState<Set<string>>(new Set());

  const {
    data: tasksData,
    error: tasksError,
    isLoading: tasksLoading,
    isValidating: tasksValidating,
  } = useEscalatingTasks(projectId);

  const {
    data: decisionsData,
    error: decisionsError,
    isLoading: decisionsLoading,
    isValidating: decisionsValidating,
  } = useDecisions(projectId);

  const {
    data: suggestionsData,
    error: suggestionsError,
    isLoading: suggestionsLoading,
    isValidating: suggestionsValidating,
  } = useSuggestions(projectId);

  // Only show skeleton on very first load (all sources have no data yet)
  const initialLoading = tasksLoading && decisionsLoading && suggestionsLoading;

  // Show subtle revalidation indicator when we already have data but something is fetching
  const hasAnyData = Boolean(tasksData || decisionsData || suggestionsData);
  const isRevalidating =
    hasAnyData && (tasksValidating || decisionsValidating || suggestionsValidating);

  // Collect per-source errors only when that source produced no data
  const sourceErrors: string[] = [];
  if (tasksError && !tasksData) sourceErrors.push('Escalations');
  if (decisionsError && !decisionsData) sourceErrors.push('Decisions');
  if (suggestionsError && !suggestionsData) sourceErrors.push('Suggestions');

  // Build unified item list from whatever data is available
  const items: AttentionItem[] = [];

  for (const t of tasksData?.tasks ?? []) {
    const task = t as unknown as { id: string; title?: string };
    items.push({ id: task.id, kind: 'escalation', label: task.title ?? task.id });
  }

  for (const d of (decisionsData ?? []) as Decision[]) {
    items.push({ id: d.id, kind: 'decision', label: d.outcome || d.citation || 'Pending decision' });
  }

  const pendingSuggestions = (suggestionsData?.suggestions ?? []).filter(
    (s) => s.status === 'pending'
  );
  for (const s of pendingSuggestions) {
    items.push({ id: s.id, kind: 'suggestion', label: s.title ?? s.summary ?? s.id });
  }

  const kindOrder: Record<ItemKind, number> = { escalation: 0, decision: 1, suggestion: 2 };
  items.sort((a, b) => kindOrder[a.kind] - kindOrder[b.kind]);

  const visibleItems = items.filter((i) => !dismissed.has(i.id)).slice(0, MAX_ITEMS);

  const dismissItem = (id: string) => setDismissed((prev) => new Set([...prev, id]));

  const handleDecisionDismiss = async (id: string) => {
    setActing((prev) => new Set([...prev, id]));
    dismissItem(id);
    try {
      await apiFetch(`/api/decisions/${encodeURIComponent(id)}`, { method: 'DELETE' });
    } catch {
      setDismissed((prev) => {
        const n = new Set(prev);
        n.delete(id);
        return n;
      });
    } finally {
      setActing((prev) => {
        const n = new Set(prev);
        n.delete(id);
        return n;
      });
    }
  };

  const handleSuggestionReject = async (id: string) => {
    setActing((prev) => new Set([...prev, id]));
    dismissItem(id);
    try {
      await apiFetch(`/api/suggestions/${encodeURIComponent(id)}/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'reject', project: projectId }),
      });
    } catch {
      setDismissed((prev) => {
        const n = new Set(prev);
        n.delete(id);
        return n;
      });
    } finally {
      setActing((prev) => {
        const n = new Set(prev);
        n.delete(id);
        return n;
      });
    }
  };

  if (initialLoading) {
    return <div className="text-sm text-gray-500 dark:text-gray-400 py-2">Loading…</div>;
  }

  return (
    <div>
      {/* Subtle revalidation indicator — only when stale data is already shown */}
      {isRevalidating && (
        <div className="text-xs text-gray-400 dark:text-gray-500 mb-1 px-1">Refreshing…</div>
      )}

      {/* Per-source error badges — only for sources with no data */}
      {sourceErrors.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {sourceErrors.map((src) => (
            <span
              key={src}
              className="text-xs px-1.5 py-0.5 rounded bg-red-100 text-red-600 dark:bg-red-900/40 dark:text-red-400"
            >
              {src} unavailable
            </span>
          ))}
        </div>
      )}

      {visibleItems.length === 0 && sourceErrors.length === 0 && (
        <div className="text-sm text-gray-500 dark:text-gray-400 py-2 text-center">All clear ✓</div>
      )}

      {visibleItems.length > 0 && (
        <ul className="space-y-2">
          {visibleItems.map((item) => (
            <li
              key={item.id}
              className="flex items-center gap-2 rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2"
            >
              <span
                className={[
                  'shrink-0 text-xs font-semibold px-1.5 py-0.5 rounded',
                  item.kind === 'escalation'
                    ? 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300'
                    : item.kind === 'decision'
                    ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300'
                    : 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
                ].join(' ')}
              >
                {item.kind === 'escalation' ? 'ESC' : item.kind === 'decision' ? 'DEC' : 'SUG'}
              </span>

              <span className="flex-1 text-sm text-gray-700 dark:text-gray-200 truncate">
                {item.label}
              </span>

              {item.kind === 'escalation' && (
                <Link
                  href="/escalations"
                  className="shrink-0 text-xs font-medium px-2 py-1 rounded bg-red-600 text-white hover:bg-red-700 transition-colors"
                >
                  Review
                </Link>
              )}

              {item.kind === 'decision' && (
                <button
                  onClick={() => handleDecisionDismiss(item.id)}
                  disabled={acting.has(item.id)}
                  aria-label="Dismiss decision"
                  className="shrink-0 text-xs px-2 py-1 rounded bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Dismiss
                </button>
              )}

              {item.kind === 'suggestion' && (
                <div className="flex shrink-0 gap-1">
                  <Link
                    href="/suggestions"
                    aria-label="Review suggestion"
                    className="text-xs px-2 py-1 rounded bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300 hover:bg-green-200 dark:hover:bg-green-800 transition-colors"
                  >
                    Review
                  </Link>
                  <button
                    onClick={() => handleSuggestionReject(item.id)}
                    disabled={acting.has(item.id)}
                    aria-label="Reject suggestion"
                    className="text-xs px-2 py-1 rounded bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    ✕
                  </button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
