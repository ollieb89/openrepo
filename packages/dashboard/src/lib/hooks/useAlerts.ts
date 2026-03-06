'use client'
import { useMemo } from 'react'
import { useLiveEvents, type LiveEvent } from './useLiveEvents'

export const ALERT_EVENT_TYPES = ['agent_failure', 'escalation', 'task_timeout', 'api_error'] as const
export type AlertEventType = typeof ALERT_EVENT_TYPES[number]

export type Alert = {
  id: number
  type: AlertEventType
  message: string | undefined
  rawAt: number
  severity: 'critical' | 'warning'
}

export function toSeverity(type: AlertEventType): 'critical' | 'warning' {
  return type === 'agent_failure' || type === 'escalation' ? 'critical' : 'warning'
}

/** Pure function — testable without React */
export function classifyAlerts(events: LiveEvent[]): Alert[] {
  return events
    .filter((e): e is LiveEvent & { type: AlertEventType } =>
      (ALERT_EVENT_TYPES as readonly string[]).includes(e.type)
    )
    .map(e => ({
      id: e.id,
      type: e.type as AlertEventType,
      message: e.message,
      rawAt: e.rawAt,
      severity: toSeverity(e.type as AlertEventType),
    }))
}

export function useAlerts(projectId?: string | null): { alerts: Alert[] } {
  const { events } = useLiveEvents(projectId ?? null)
  const alerts = useMemo(() => classifyAlerts(events), [events])
  return { alerts }
}
