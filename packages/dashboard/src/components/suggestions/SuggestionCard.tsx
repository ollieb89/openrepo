'use client';

import { useState } from 'react';
import type { Suggestion } from '@/lib/types/suggestions';

interface SuggestionCardProps {
  suggestion: Suggestion;
  onAccept: (s: Suggestion) => Promise<void>;
  onReject: (s: Suggestion, reason: string) => Promise<void>;
}

export default function SuggestionCard({ suggestion, onAccept, onReject }: SuggestionCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [rejecting, setRejecting] = useState(false);
  const [rejectReason, setRejectReason] = useState('');
  const [accepting, setAccepting] = useState(false);
  const [accepted, setAccepted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleAccept() {
    setAccepting(true);
    setError(null);
    try {
      await onAccept(suggestion);
      setAccepted(true);
    } catch {
      setError('Accept failed');
    } finally {
      setAccepting(false);
    }
  }

  async function handleDismiss() {
    try {
      await onReject(suggestion, rejectReason);
    } catch {
      setError('Reject failed');
    }
  }

  if (accepted) {
    return (
      <div className="rounded-lg border border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/20 px-4 py-3">
        <p className="text-sm text-gray-700 dark:text-gray-300 font-medium">{suggestion.pattern_description}</p>
        <span className="text-green-600 dark:text-green-400 text-sm mt-1 inline-block">Applied to soul-override.md</span>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-4 py-3 space-y-2">
      {/* Header row */}
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm font-medium text-gray-900 dark:text-white flex-1">
          {suggestion.pattern_description}
        </p>
        <span className="inline-flex items-center rounded-full bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300 text-xs font-semibold px-2 py-0.5 whitespace-nowrap">
          {suggestion.evidence_count} occurrence{suggestion.evidence_count !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Expanded diff + evidence */}
      {expanded && (
        <div className="space-y-2">
          <pre className="bg-gray-900 text-gray-100 p-3 rounded text-xs overflow-auto font-mono whitespace-pre-wrap">
            {suggestion.diff_text}
          </pre>
          {suggestion.evidence_examples.length > 0 && (
            <ul className="space-y-1">
              {suggestion.evidence_examples.slice(0, 3).map((ex, i) => (
                <li key={i} className="text-xs text-gray-500 dark:text-gray-400">
                  <span className="font-mono text-gray-600 dark:text-gray-300">{ex.task_id}:</span> {ex.excerpt}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Action row */}
      <div className="flex items-center justify-between gap-2">
        <button
          type="button"
          onClick={() => setExpanded(v => !v)}
          className="text-xs text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1"
        >
          {expanded ? (
            <>
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
              </svg>
              Hide diff
            </>
          ) : (
            <>
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
              </svg>
              Show diff
            </>
          )}
        </button>

        <div className="flex items-center gap-2">
          {error && <span className="text-xs text-red-600 dark:text-red-400">{error}</span>}
          {!rejecting ? (
            <>
              <button
                type="button"
                onClick={() => setRejecting(true)}
                className="rounded-md border border-gray-300 dark:border-gray-600 px-3 py-1 text-xs font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              >
                Reject
              </button>
              <button
                type="button"
                onClick={handleAccept}
                disabled={accepting}
                className="rounded-md bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed px-3 py-1 text-xs font-medium text-white transition-colors"
              >
                {accepting ? 'Accepting...' : 'Accept'}
              </button>
            </>
          ) : (
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={rejectReason}
                onChange={e => setRejectReason(e.target.value)}
                placeholder="Why reject? (optional)"
                className="rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-2 py-1 text-xs text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500 w-48"
              />
              <button
                type="button"
                onClick={handleDismiss}
                className="rounded-md bg-gray-600 hover:bg-gray-700 px-3 py-1 text-xs font-medium text-white transition-colors"
              >
                Dismiss
              </button>
              <button
                type="button"
                onClick={() => { setRejecting(false); setRejectReason(''); }}
                className="rounded-md border border-gray-300 dark:border-gray-600 px-3 py-1 text-xs font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              >
                Cancel
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
