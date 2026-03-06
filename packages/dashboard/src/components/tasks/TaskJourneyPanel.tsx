'use client'

import type { Task } from '@/lib/types'

export type Journey = {
  dispatched_at: number | null
  assigned_at: number | null
  branch: string | null
  completed_at: number | null
  stage: string
}

type Props = {
  task: Task
}

/**
 * Build a Journey object from Task fields.
 * Exported for unit testing.
 */
export function buildJourney(task: Task): Journey {
  const meta = task.metadata as Record<string, unknown>

  const branch =
    typeof meta?.l3_branch === 'string' ? meta.l3_branch : null

  const assignedAt =
    typeof meta?.started_at === 'number'
      ? (meta.started_at as number)
      : null

  const completedAt =
    typeof meta?.completed_at === 'number'
      ? (meta.completed_at as number)
      : task.status === 'completed' || task.status === 'failed' || task.status === 'rejected'
        ? task.updated_at
        : null

  return {
    dispatched_at: task.created_at ?? null,
    assigned_at: assignedAt,
    branch,
    completed_at: completedAt,
    stage: task.status,
  }
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

const STAGE_LABELS = [
  { key: 'dispatched_at' as const, label: 'L1 Dispatch' },
  { key: 'assigned_at' as const, label: 'L2 Assignment' },
  { key: 'assigned_at' as const, label: 'L3 Execution', showBranch: true },
  { key: 'completed_at' as const, label: 'Completion' },
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
                {fmtTimestamp(journey[s.key])}
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
