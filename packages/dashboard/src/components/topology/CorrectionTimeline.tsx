'use client';

import React, { useState } from 'react';
import type { ChangelogEntry, TopologyDiff } from '@/lib/types/topology';

// ---------------------------------------------------------------------------
// Pure utility functions (exported for unit testing)
// ---------------------------------------------------------------------------

/**
 * Sort changelog entries chronologically by timestamp (oldest first).
 */
export function sortChangelog(entries: ChangelogEntry[]): ChangelogEntry[] {
  return [...entries].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
  );
}

export interface DiffLine {
  type: 'added' | 'removed' | 'modified';
  text: string;
}

/**
 * Extract flat colored diff lines from a TopologyDiff object.
 * Returns an empty array if diff is undefined or null.
 */
export function extractDiffLines(diff: TopologyDiff | undefined | null): DiffLine[] {
  if (!diff) return [];

  const lines: DiffLine[] = [];

  for (const n of diff.added_nodes ?? []) {
    lines.push({ type: 'added', text: `+ ${n.id} (node)` });
  }
  for (const n of diff.removed_nodes ?? []) {
    lines.push({ type: 'removed', text: `- ${n.id} (node)` });
  }
  for (const n of diff.modified_nodes ?? []) {
    lines.push({ type: 'modified', text: `~ ${n.id} (node)` });
  }
  for (const e of diff.added_edges ?? []) {
    lines.push({ type: 'added', text: `+ ${e.from_role} -> ${e.to_role} (edge)` });
  }
  for (const e of diff.removed_edges ?? []) {
    lines.push({ type: 'removed', text: `- ${e.from_role} -> ${e.to_role} (edge)` });
  }
  for (const e of diff.modified_edges ?? []) {
    lines.push({ type: 'modified', text: `~ ${e.from_role} -> ${e.to_role} (edge)` });
  }

  return lines;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

const CORRECTION_BADGE: Record<ChangelogEntry['correction_type'], string> = {
  initial: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
  soft:    'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
  hard:    'bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300',
};

const CORRECTION_LABEL: Record<ChangelogEntry['correction_type'], string> = {
  initial: 'Initial',
  soft:    'Soft',
  hard:    'Hard',
};

const DIFF_LINE_STYLE: Record<DiffLine['type'], string> = {
  added:    'text-green-700 dark:text-green-400',
  removed:  'text-red-700 dark:text-red-400',
  modified: 'text-yellow-700 dark:text-yellow-400',
};

function formatTimestamp(ts: string): string {
  try {
    return new Date(ts).toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return ts;
  }
}

interface CorrectionCardProps {
  entry: ChangelogEntry;
  index: number;
  selected: boolean;
  onClick: () => void;
}

function CorrectionCard({ entry, index, selected, onClick }: CorrectionCardProps) {
  const [expanded, setExpanded] = useState(false);
  const diffLines = extractDiffLines(entry.diff);
  const hasDiff = diffLines.length > 0;

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e) => e.key === 'Enter' && onClick()}
      className={[
        'relative flex flex-col gap-2 p-3 rounded-lg border cursor-pointer transition-all',
        'bg-white dark:bg-gray-900',
        selected
          ? 'border-blue-500 ring-2 ring-blue-400/50 dark:border-blue-400'
          : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600',
      ].join(' ')}
    >
      {/* Header row */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          <span
            className={`px-2 py-0.5 rounded-full text-[11px] font-bold ${CORRECTION_BADGE[entry.correction_type]}`}
          >
            {CORRECTION_LABEL[entry.correction_type]}
          </span>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            #{index + 1}
          </span>
        </div>
        <span className="text-[11px] text-gray-400 dark:text-gray-500 whitespace-nowrap flex-shrink-0">
          {formatTimestamp(entry.timestamp)}
        </span>
      </div>

      {/* Summary */}
      {entry.diff?.summary && (
        <p className="text-sm text-gray-700 dark:text-gray-300 leading-snug">
          {entry.diff.summary}
        </p>
      )}

      {/* Pushback note — amber callout block */}
      {entry.annotations?.pushback_note && (
        <div className="flex gap-2 p-2 rounded bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800">
          <span className="text-amber-500 flex-shrink-0 mt-0.5">!</span>
          <p className="text-xs text-amber-800 dark:text-amber-300 leading-snug">
            {entry.annotations.pushback_note}
          </p>
        </div>
      )}

      {/* Expandable diff section */}
      {hasDiff && (
        <div>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              setExpanded((v) => !v);
            }}
            className="flex items-center gap-1 text-[11px] text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
          >
            <span>{expanded ? '▾' : '▸'}</span>
            <span>{expanded ? 'Hide diff' : `Show diff (${diffLines.length} changes)`}</span>
          </button>

          {expanded && (
            <div className="mt-1 p-2 rounded bg-gray-50 dark:bg-gray-800 border border-gray-100 dark:border-gray-700 font-mono text-[11px] space-y-0.5">
              {diffLines.map((line, i) => (
                <div key={i} className={DIFF_LINE_STYLE[line.type]}>
                  {line.text}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// CorrectionTimeline
// ---------------------------------------------------------------------------

interface CorrectionTimelineProps {
  changelog: ChangelogEntry[];
  selectedIndex: number | null;
  onSelectEvent: (index: number) => void;
}

export function CorrectionTimeline({
  changelog,
  selectedIndex,
  onSelectEvent,
}: CorrectionTimelineProps) {
  const sorted = sortChangelog(changelog);

  if (!sorted.length) {
    return (
      <div className="flex flex-col items-center justify-center py-10 text-gray-400 dark:text-gray-600">
        <div className="text-3xl mb-2">◌</div>
        <p className="text-sm">No corrections yet</p>
      </div>
    );
  }

  return (
    <div className="relative flex flex-col">
      {/* Vertical connecting line */}
      <div
        className="absolute left-[9px] top-4 bottom-4 w-0.5 bg-gray-200 dark:bg-gray-700"
        aria-hidden="true"
      />

      <div className="flex flex-col gap-3">
        {sorted.map((entry, i) => (
          <div key={`${entry.timestamp}-${i}`} className="flex gap-3">
            {/* Timeline dot */}
            <div className="relative z-10 flex-shrink-0 mt-3">
              <div
                className={[
                  'w-4 h-4 rounded-full border-2 transition-colors',
                  selectedIndex === i
                    ? 'bg-blue-500 border-blue-500'
                    : 'bg-white dark:bg-gray-900 border-gray-300 dark:border-gray-600',
                ].join(' ')}
              />
            </div>

            {/* Card */}
            <div className="flex-1 min-w-0">
              <CorrectionCard
                entry={entry}
                index={i}
                selected={selectedIndex === i}
                onClick={() => onSelectEvent(i)}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default CorrectionTimeline;
