import { describe, it, expect } from 'vitest'
import { classifyAlerts } from '@/lib/hooks/useAlerts'
import type { LiveEvent } from '@/lib/hooks/useLiveEvents'

const makeEvent = (overrides: Partial<LiveEvent>): LiveEvent => ({
  id: 0,
  type: 'task_started',
  rawAt: Date.now(),
  ...overrides,
})

describe('classifyAlerts', () => {
  it('filters only alert event types', () => {
    const events: LiveEvent[] = [
      makeEvent({ id: 1, type: 'agent_failure' }),
      makeEvent({ id: 2, type: 'task_timeout' }),
      makeEvent({ id: 3, type: 'task_started' }),
    ]
    const alerts = classifyAlerts(events)
    expect(alerts).toHaveLength(2)
    expect(alerts.every(a => ['agent_failure', 'task_timeout'].includes(a.type))).toBe(true)
  })

  it('classifies agent_failure as critical', () => {
    const events: LiveEvent[] = [makeEvent({ id: 1, type: 'agent_failure' })]
    const alerts = classifyAlerts(events)
    expect(alerts[0].severity).toBe('critical')
  })

  it('classifies escalation as critical', () => {
    const events: LiveEvent[] = [makeEvent({ id: 2, type: 'escalation' })]
    const alerts = classifyAlerts(events)
    expect(alerts[0].severity).toBe('critical')
  })

  it('classifies task_timeout as warning', () => {
    const events: LiveEvent[] = [makeEvent({ id: 3, type: 'task_timeout' })]
    const alerts = classifyAlerts(events)
    expect(alerts[0].severity).toBe('warning')
  })

  it('classifies api_error as warning', () => {
    const events: LiveEvent[] = [makeEvent({ id: 4, type: 'api_error' })]
    const alerts = classifyAlerts(events)
    expect(alerts[0].severity).toBe('warning')
  })

  it('returns empty array when no alert events', () => {
    const events: LiveEvent[] = [
      makeEvent({ id: 1, type: 'task_started' }),
      makeEvent({ id: 2, type: 'task_completed' }),
    ]
    expect(classifyAlerts(events)).toHaveLength(0)
  })

  it('maps rawAt to timestamp', () => {
    const rawAt = 1741255200000
    const events: LiveEvent[] = [makeEvent({ id: 1, type: 'agent_failure', rawAt })]
    const alerts = classifyAlerts(events)
    expect(alerts[0].rawAt).toBe(rawAt)
  })
})
