'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { apiJson, apiFetch } from '@/lib/api-client';
import { useProject } from '@/context/ProjectContext';
import type { Decision } from '@/lib/types/decisions';

type ItemKind = 'escalation' | 'decision' | 'suggestion';

interface AttentionItem {
  id: string;
  kind: ItemKind;
  label: string;
}

interface SuggestionRecord {
  id: string;
  status: string;
  evidence_count: number;
  title?: string;
  summary?: string;
}

interface SuggestionsResponse {
  version: string;
  last_run: number | null;
  suggestions: SuggestionRecord[];
}

const MAX_ITEMS = 5;
const POLL_INTERVAL_MS = 30_000;

export default function AttentionQueue() {
  const { projectId } = useProject();
  const [items, setItems] = useState<AttentionItem[]>([]);
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());
  const [acting, setActing] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);

  const loadItems = useCallback(async () => {
    if (!projectId) return;

    const next: AttentionItem[] = [];

    // Escalations — fetched from /api/tasks?state=escalating
    try {
      const { tasks: escalatedTasks } = await apiJson<{ tasks: Array<{ id: string; title?: string }> }>(
        `/api/tasks?state=escalating&project=${encodeURIComponent(projectId)}`
      );
      for (const t of Array.isArray(escalatedTasks) ? escalatedTasks : []) {
        next.push({
          id: t.id,
          kind: 'escalation',
          label: t.title ?? t.id,
        });
      }
    } catch {
      // Silently degrade
    }

    // Decisions — returns Decision[] directly
    try {
      const decisions = await apiJson<Decision[]>(
        `/api/decisions?projectId=${encodeURIComponent(projectId)}`
      );
      for (const d of decisions) {
        next.push({
          id: d.id,
          kind: 'decision',
          label: d.outcome || d.citation || 'Pending decision',
        });
      }
    } catch {
      // Silently degrade
    }

    // Suggestions — returns { suggestions: SuggestionRecord[] }
    try {
      const data = await apiJson<SuggestionsResponse>(
        `/api/suggestions?project=${encodeURIComponent(projectId)}`
      );
      const pending = (data.suggestions ?? []).filter(
        (s) => s.status === 'pending' || s.status === 'new'
      );
      for (const s of pending) {
        next.push({
          id: s.id,
          kind: 'suggestion',
          label: s.title ?? s.summary ?? s.id,
        });
      }
    } catch {
      // Silently degrade
    }

    // Sort: escalations first, then decisions, then suggestions
    const kindOrder: Record<ItemKind, number> = {
      escalation: 0,
      decision: 1,
      suggestion: 2,
    };
    next.sort((a, b) => kindOrder[a.kind] - kindOrder[b.kind]);

    setItems(next);
    const nextIds = new Set(next.map(i => i.id));
    setDismissed(prev => new Set([...prev].filter(id => nextIds.has(id))));
    setLoading(false);
  }, [projectId]);

  useEffect(() => {
    loadItems();
    const interval = setInterval(loadItems, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [loadItems]);

  const dismissItem = (id: string) => {
    setDismissed((prev) => new Set([...prev, id]));
  };

  const handleDecisionAction = async (id: string) => {
    setActing(prev => new Set([...prev, id]));
    dismissItem(id);
    try {
      await apiFetch(`/api/decisions/${encodeURIComponent(id)}`, { method: 'DELETE' });
    } catch {
      setDismissed(prev => { const n = new Set(prev); n.delete(id); return n; });
    } finally {
      setActing(prev => { const n = new Set(prev); n.delete(id); return n; });
    }
  };

  const handleSuggestionAction = async (
    id: string,
    action: 'accept' | 'reject'
  ) => {
    setActing(prev => new Set([...prev, id]));
    dismissItem(id);
    try {
      await apiFetch(`/api/suggestions/${encodeURIComponent(id)}/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, project: projectId }),
      });
    } catch {
      setDismissed(prev => { const n = new Set(prev); n.delete(id); return n; });
    } finally {
      setActing(prev => { const n = new Set(prev); n.delete(id); return n; });
    }
  };

  const visibleItems = items
    .filter((item) => !dismissed.has(item.id))
    .slice(0, MAX_ITEMS);

  if (loading) {
    return (
      <div className="text-sm text-gray-500 dark:text-gray-400 py-2">
        Loading...
      </div>
    );
  }

  if (visibleItems.length === 0) {
    return (
      <div className="text-sm text-gray-500 dark:text-gray-400 py-2 text-center">
        All clear ✓
      </div>
    );
  }

  return (
    <ul className="space-y-2">
      {visibleItems.map((item) => (
        <li
          key={item.id}
          className="flex items-center gap-2 rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2"
        >
          {/* Kind badge */}
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
            {item.kind === 'escalation'
              ? 'ESC'
              : item.kind === 'decision'
              ? 'DEC'
              : 'SUG'}
          </span>

          {/* Label */}
          <span className="flex-1 text-sm text-gray-700 dark:text-gray-200 truncate">
            {item.label}
          </span>

          {/* Actions */}
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
              onClick={() => handleDecisionAction(item.id)}
              disabled={acting.has(item.id)}
              aria-label="Mark decision as done"
              className="shrink-0 text-xs px-2 py-1 rounded bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Done
            </button>
          )}

          {item.kind === 'suggestion' && (
            <div className="flex shrink-0 gap-1">
              <button
                onClick={() => handleSuggestionAction(item.id, 'accept')}
                disabled={acting.has(item.id)}
                aria-label="Accept suggestion"
                className="text-xs px-2 py-1 rounded bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300 hover:bg-green-200 dark:hover:bg-green-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                ✓
              </button>
              <button
                onClick={() => handleSuggestionAction(item.id, 'reject')}
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
  );
}
