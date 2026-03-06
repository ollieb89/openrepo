import { describe, it, expect } from 'vitest'
import { alertFeedRows } from '@/components/common/AlertFeed'
import type { Alert } from '@/lib/hooks/useAlerts'

function makeAlert(overrides: Partial<Alert> = {}): Alert {
  return {
    id: 1,
    type: 'agent_failure',
    message: 'L3 crashed',
    rawAt: 1741255200000,
    severity: 'critical',
    ...overrides,
  }
}

describe('alertFeedRows', () => {
  it('returns empty array for empty alerts', () => {
    expect(alertFeedRows([])).toHaveLength(0)
  })

  it('returns one row per alert', () => {
    const alerts = [
      makeAlert({ id: 1, type: 'agent_failure', severity: 'critical' }),
      makeAlert({ id: 2, type: 'task_timeout', severity: 'warning' }),
    ]
    expect(alertFeedRows(alerts)).toHaveLength(2)
  })

  it('formats type with spaces replacing underscores', () => {
    const alerts = [makeAlert({ type: 'agent_failure' })]
    const rows = alertFeedRows(alerts)
    expect(rows[0].label).toBe('agent failure')
  })

  it('includes severity in each row', () => {
    const alerts = [
      makeAlert({ id: 1, severity: 'critical' }),
      makeAlert({ id: 2, type: 'task_timeout', severity: 'warning' }),
    ]
    const rows = alertFeedRows(alerts)
    expect(rows[0].severity).toBe('critical')
    expect(rows[1].severity).toBe('warning')
  })

  it('includes message in each row', () => {
    const alerts = [makeAlert({ message: 'Container OOM' })]
    const rows = alertFeedRows(alerts)
    expect(rows[0].message).toBe('Container OOM')
  })
})
