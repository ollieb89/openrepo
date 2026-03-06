'use client'
import { useEffect, useRef } from 'react'
import { toast } from 'react-toastify'
import { useAlerts } from '@/lib/hooks/useAlerts'

export function AlertToastEmitter({ projectId }: { projectId?: string | null }) {
  const { alerts } = useAlerts(projectId)
  const seenIds = useRef(new Set<number>())

  useEffect(() => {
    alerts.forEach(a => {
      if (a.severity === 'critical' && !seenIds.current.has(a.id)) {
        seenIds.current.add(a.id)
        toast.error(`${a.type.replace(/_/g, ' ')}: ${a.message ?? ''}`, {
          toastId: String(a.id),
        })
      }
    })
  }, [alerts])

  return null
}
