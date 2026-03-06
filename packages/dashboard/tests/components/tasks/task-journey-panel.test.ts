import { describe, it, expect } from 'vitest'
import { buildJourney, fmtTimestamp } from '@/components/tasks/TaskJourneyPanel'
import type { Task } from '@/lib/types'

function makeTask(overrides: Partial<Task> = {}): Task {
  return {
    id: 'task-1',
    status: 'completed',
    skill_hint: 'test',
    activity_log: [],
    created_at: 1741255200,  // 2026-03-06T10:00:00Z in seconds
    updated_at: 1741255500,  // 2026-03-06T10:05:00Z in seconds
    metadata: {},
    ...overrides,
  }
}

describe('buildJourney', () => {
  it('sets dispatched_at from task.created_at', () => {
    const task = makeTask()
    const journey = buildJourney(task)
    expect(journey.dispatched_at).toBe(1741255200)
  })

  it('sets stage from task.status', () => {
    const task = makeTask({ status: 'in_progress' })
    const journey = buildJourney(task)
    expect(journey.stage).toBe('in_progress')
  })

  it('sets assigned_at from metadata.started_at when present', () => {
    const task = makeTask({ metadata: { started_at: 1741255205 } })
    const journey = buildJourney(task)
    expect(journey.assigned_at).toBe(1741255205)
  })

  it('sets assigned_at to null when metadata.started_at is absent', () => {
    const task = makeTask({ status: 'pending' })
    const journey = buildJourney(task)
    expect(journey.assigned_at).toBeNull()
  })

  it('sets branch from metadata.l3_branch when present', () => {
    const task = makeTask({ metadata: { l3_branch: 'l3/task-task-1' } })
    const journey = buildJourney(task)
    expect(journey.branch).toBe('l3/task-task-1')
  })

  it('sets branch to null when metadata.l3_branch is absent', () => {
    const task = makeTask()
    const journey = buildJourney(task)
    expect(journey.branch).toBeNull()
  })

  it('sets completed_at from metadata.completed_at when present', () => {
    const task = makeTask({ metadata: { completed_at: 1741255490 } })
    const journey = buildJourney(task)
    expect(journey.completed_at).toBe(1741255490)
  })

  it('falls back to updated_at for completed_at when status is completed and no metadata', () => {
    const task = makeTask({ status: 'completed' })
    const journey = buildJourney(task)
    expect(journey.completed_at).toBe(1741255500)
  })

  it('falls back to updated_at for completed_at when status is failed', () => {
    const task = makeTask({ status: 'failed' })
    const journey = buildJourney(task)
    expect(journey.completed_at).toBe(1741255500)
  })

  it('sets completed_at to null when status is in_progress and no metadata', () => {
    const task = makeTask({ status: 'in_progress' })
    const journey = buildJourney(task)
    expect(journey.completed_at).toBeNull()
  })

  it('returns all four required keys', () => {
    const task = makeTask()
    const journey = buildJourney(task)
    expect(Object.keys(journey)).toContain('dispatched_at')
    expect(Object.keys(journey)).toContain('assigned_at')
    expect(Object.keys(journey)).toContain('branch')
    expect(Object.keys(journey)).toContain('completed_at')
    expect(Object.keys(journey)).toContain('stage')
  })
})

describe('fmtTimestamp', () => {
  it('returns "—" for null', () => {
    expect(fmtTimestamp(null)).toBe('—')
  })

  it('returns a non-empty string for a valid unix timestamp (seconds)', () => {
    const result = fmtTimestamp(1741255200)
    expect(result).not.toBe('—')
    expect(result.length).toBeGreaterThan(0)
  })
})
