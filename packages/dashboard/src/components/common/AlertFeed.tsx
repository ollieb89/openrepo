'use client'
import type { Alert } from '@/lib/hooks/useAlerts'

export type AlertRow = {
  id: number
  label: string
  message: string | undefined
  severity: 'critical' | 'warning'
  rawAt: number
}

/** Pure helper — exported for testing */
export function alertFeedRows(alerts: Alert[]): AlertRow[] {
  return alerts.map(a => ({
    id: a.id,
    label: a.type.replace(/_/g, ' '),
    message: a.message,
    severity: a.severity,
    rawAt: a.rawAt,
  }))
}

const severityStyles: Record<'critical' | 'warning', string> = {
  critical: 'bg-red-50 dark:bg-red-950 border-red-200 dark:border-red-800 text-red-800 dark:text-red-200',
  warning: 'bg-yellow-50 dark:bg-yellow-950 border-yellow-200 dark:border-yellow-800 text-yellow-800 dark:text-yellow-200',
}

export function AlertFeed({ alerts }: { alerts: Alert[] }) {
  if (alerts.length === 0) {
    return (
      <p className="text-sm text-gray-400 dark:text-gray-500 text-center py-4">No alerts</p>
    )
  }

  const rows = alertFeedRows(alerts)

  return (
    <ul className="space-y-2">
      {rows.map(r => (
        <li key={r.id} className={`rounded border px-3 py-2 text-xs ${severityStyles[r.severity]}`}>
          <div className="flex items-center justify-between gap-2">
            <span className="font-medium uppercase tracking-wide">{r.label}</span>
            <span className="opacity-60">{new Date(r.rawAt).toLocaleTimeString()}</span>
          </div>
          {r.message && <p className="mt-0.5 opacity-80">{r.message}</p>}
        </li>
      ))}
    </ul>
  )
}
