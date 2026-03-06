import type { Task } from '@/lib/types'

export type Journey = {
  dispatched_at: number | null
  assigned_at: number | null
  branch: string | null
  completed_at: number | null
  stage: string
}

/**
 * Build a Journey object from Task fields.
 * Shared between TaskJourneyPanel (client component) and the tasks/[id] API route.
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
