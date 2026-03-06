'use client'

import type { Task } from '@/lib/types'
import { buildJourney } from '@/lib/journey-utils'

// Re-export Journey type and buildJourney for consumers that import from this module.
export type { Journey } from '@/lib/journey-utils'
export { buildJourney } from '@/lib/journey-utils'

type Props = {
  task: Task
}

/**
 * Format a Unix timestamp (seconds) to a human-readable time string.
 * Exported for unit testing.
 */
export function fmtTimestamp(ts: number | null): string {
  if (ts === null) return '—'
  return new Date(ts * 1000).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

// NOTE: L3 execution start time is not separately tracked in the data model yet;
// the stage shows branch name only for now.
// TODO: add a dedicated l3_started_at field to task metadata when L3 timing is instrumented.
const STAGE_LABELS = [
  { key: 'dispatched_at' as const, label: 'L1 Dispatch', l3Stage: false },
  { key: 'assigned_at' as const,   label: 'L2 Assignment', l3Stage: false },
  { key: 'assigned_at' as const,   label: 'L3 Execution', showBranch: true, l3Stage: true },
  { key: 'completed_at' as const,  label: 'Completion', l3Stage: false },
]

export function TaskJourneyPanel({ task }: Props) {
  const journey = buildJourney(task)

  return (
    <div className="p-4 bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700">
      <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
        Task Journey
      </h3>
      <ol className="space-y-3">
        {STAGE_LABELS.map((s, i) => (
          <li key={i} className="flex items-start gap-3">
            <span className="mt-0.5 w-5 h-5 rounded-full bg-indigo-100 dark:bg-indigo-900 flex items-center justify-center text-xs text-indigo-700 dark:text-indigo-300 shrink-0">
              {i + 1}
            </span>
            <div>
              <div className="text-xs font-medium text-gray-700 dark:text-gray-300">
                {s.label}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400">
                {/* L3 Execution: show "—" — start time is not separately tracked yet */}
                {s.l3Stage ? '—' : fmtTimestamp(journey[s.key])}
              </div>
              {s.showBranch && journey.branch && (
                <div className="mt-0.5 text-xs font-mono text-indigo-600 dark:text-indigo-400">
                  {journey.branch}
                </div>
              )}
            </div>
          </li>
        ))}
      </ol>
    </div>
  )
}
