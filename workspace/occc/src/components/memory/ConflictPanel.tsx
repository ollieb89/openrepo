'use client';

import { useState } from 'react';
import type { MemoryItem } from '@/lib/types/memory';

interface ConflictPanelProps {
  flaggedItem: MemoryItem;
  conflictItem: MemoryItem;
  similarityScore: number;
  onEdit: (id: string, content: string) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
  onDismiss: () => void;
  onClose: () => void;
  onAdvanceNext: () => void;
}

// Simple word-level diff using LCS approach
// Returns array of tokens with annotations
type DiffToken = { word: string; type: 'common' | 'added' | 'removed' };

function computeWordDiff(aText: string, bText: string): { aTokens: DiffToken[]; bTokens: DiffToken[] } {
  const aWords = aText ? aText.split(/(\s+)/) : [];
  const bWords = bText ? bText.split(/(\s+)/) : [];

  // LCS DP table (word-level)
  const m = aWords.length;
  const n = bWords.length;
  const dp: number[][] = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0));

  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      if (aWords[i - 1] === bWords[j - 1]) {
        dp[i][j] = dp[i - 1][j - 1] + 1;
      } else {
        dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
      }
    }
  }

  // Backtrack to build diff
  const aTokens: DiffToken[] = [];
  const bTokens: DiffToken[] = [];

  let i = m;
  let j = n;
  const aResult: DiffToken[] = [];
  const bResult: DiffToken[] = [];

  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && aWords[i - 1] === bWords[j - 1]) {
      aResult.unshift({ word: aWords[i - 1], type: 'common' });
      bResult.unshift({ word: bWords[j - 1], type: 'common' });
      i--;
      j--;
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      bResult.unshift({ word: bWords[j - 1], type: 'added' });
      j--;
    } else if (i > 0) {
      aResult.unshift({ word: aWords[i - 1], type: 'removed' });
      i--;
    }
  }

  aTokens.push(...aResult);
  bTokens.push(...bResult);

  return { aTokens, bTokens };
}

function DiffView({ tokens }: { tokens: DiffToken[] }) {
  return (
    <p className="text-sm text-gray-800 dark:text-gray-200 whitespace-pre-wrap break-words leading-relaxed">
      {tokens.map((token, idx) => {
        if (token.type === 'common') {
          return <span key={idx}>{token.word}</span>;
        }
        if (token.type === 'added') {
          return (
            <mark
              key={idx}
              className="bg-green-200 dark:bg-green-900/60 text-green-900 dark:text-green-200 rounded-sm"
            >
              {token.word}
            </mark>
          );
        }
        // removed
        return (
          <mark
            key={idx}
            className="bg-red-200 dark:bg-red-900/60 text-red-900 dark:text-red-200 line-through rounded-sm"
          >
            {token.word}
          </mark>
        );
      })}
    </p>
  );
}

export default function ConflictPanel({
  flaggedItem,
  conflictItem,
  similarityScore,
  onEdit,
  onDelete,
  onDismiss,
  onClose,
  onAdvanceNext,
}: ConflictPanelProps) {
  const [editing, setEditing] = useState(false);
  const [editContent, setEditContent] = useState(flaggedItem.content ?? '');
  const [resolving, setResolving] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  const similarityPct = Math.round(similarityScore * 100);

  const aContent = flaggedItem.content ?? '';
  const bContent = conflictItem.content ?? '';
  const { aTokens, bTokens } = computeWordDiff(aContent, bContent);

  async function handleSave() {
    setResolving(true);
    try {
      await onEdit(flaggedItem.id, editContent);
      setEditing(false);
      onAdvanceNext();
    } finally {
      setResolving(false);
    }
  }

  async function handleDelete() {
    setResolving(true);
    try {
      await onDelete(flaggedItem.id);
      setConfirmingDelete(false);
      onAdvanceNext();
    } finally {
      setResolving(false);
    }
  }

  function handleDismiss() {
    onDismiss();
    onAdvanceNext();
  }

  const flaggedIdShort = flaggedItem.id.slice(0, 8) + '…';
  const conflictIdShort = conflictItem.id.slice(0, 8) + '…';

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/40 transition-opacity duration-300"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Slide-in panel */}
      <div
        className="fixed right-0 top-0 z-50 flex h-full w-full max-w-2xl flex-col bg-white dark:bg-gray-900 shadow-2xl translate-x-0 transition-transform duration-300"
        role="dialog"
        aria-modal="true"
        aria-label="Conflict Resolution"
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-200 dark:border-gray-700 px-6 py-4 shrink-0">
          <div className="flex items-center gap-3">
            <h2 className="text-base font-semibold text-gray-900 dark:text-white">
              Conflict Resolution
            </h2>
            <span className="inline-flex items-center rounded-full bg-red-100 dark:bg-red-900/40 px-2.5 py-0.5 text-xs font-semibold text-red-700 dark:text-red-300">
              {similarityPct}% similar
            </span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1.5 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            aria-label="Close panel"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Side-by-side content */}
        <div className="flex flex-1 overflow-hidden divide-x divide-gray-200 dark:divide-gray-700">
          {/* Memory A — flagged item */}
          <div className="flex flex-col flex-1 min-w-0 overflow-y-auto">
            <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 shrink-0">
              <p className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                Memory A
              </p>
              <p className="font-mono text-xs text-gray-600 dark:text-gray-400 truncate mt-0.5" title={flaggedItem.id}>
                {flaggedIdShort}
              </p>
            </div>
            <div className="flex-1 px-4 py-3 overflow-y-auto">
              {editing ? (
                <textarea
                  className="w-full h-full min-h-[200px] text-sm text-gray-800 dark:text-gray-200 bg-white dark:bg-gray-900 border border-blue-400 dark:border-blue-500 rounded-md p-2 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
                  value={editContent}
                  onChange={e => setEditContent(e.target.value)}
                  disabled={resolving}
                />
              ) : (
                <DiffView tokens={aTokens} />
              )}
            </div>
          </div>

          {/* Memory B — conflict item */}
          <div className="flex flex-col flex-1 min-w-0 overflow-y-auto">
            <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 shrink-0">
              <p className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                Memory B
              </p>
              <p className="font-mono text-xs text-gray-600 dark:text-gray-400 truncate mt-0.5" title={conflictItem.id}>
                {conflictIdShort}
              </p>
            </div>
            <div className="flex-1 px-4 py-3 overflow-y-auto">
              <DiffView tokens={bTokens} />
            </div>
          </div>
        </div>

        {/* Action bar */}
        <div className="shrink-0 border-t border-gray-200 dark:border-gray-700 px-6 py-4 bg-gray-50 dark:bg-gray-800">
          {confirmingDelete ? (
            /* Delete confirmation inline */
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-700 dark:text-gray-300">
                Delete Memory A? This cannot be undone.
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setConfirmingDelete(false)}
                  disabled={resolving}
                  className="rounded-md border border-gray-300 dark:border-gray-600 px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleDelete}
                  disabled={resolving}
                  className="rounded-md bg-red-600 hover:bg-red-700 px-3 py-1.5 text-sm font-medium text-white transition-colors disabled:opacity-50 flex items-center gap-1.5"
                >
                  {resolving && (
                    <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                  )}
                  Confirm Delete
                </button>
              </div>
            </div>
          ) : editing ? (
            /* Edit mode actions */
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500 dark:text-gray-400">Editing Memory A</span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => { setEditing(false); setEditContent(flaggedItem.content ?? ''); }}
                  disabled={resolving}
                  className="rounded-md border border-gray-300 dark:border-gray-600 px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleSave}
                  disabled={resolving}
                  className="rounded-md bg-blue-600 hover:bg-blue-700 px-3 py-1.5 text-sm font-medium text-white transition-colors disabled:opacity-50 flex items-center gap-1.5"
                >
                  {resolving && (
                    <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                  )}
                  Save
                </button>
              </div>
            </div>
          ) : (
            /* Default actions */
            <div className="flex items-center gap-2 justify-end">
              <button
                type="button"
                onClick={handleDismiss}
                className="rounded-md border border-gray-300 dark:border-gray-600 px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              >
                Dismiss
              </button>
              <button
                type="button"
                onClick={() => setConfirmingDelete(true)}
                className="rounded-md border border-red-200 dark:border-red-800 px-3 py-1.5 text-sm font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
              >
                Delete A
              </button>
              <button
                type="button"
                onClick={() => setEditing(true)}
                className="rounded-md bg-blue-600 hover:bg-blue-700 px-3 py-1.5 text-sm font-medium text-white transition-colors"
              >
                Edit A
              </button>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
