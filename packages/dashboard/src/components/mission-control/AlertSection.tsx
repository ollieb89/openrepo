'use client'
import { useProject } from '@/context/ProjectContext'
import { useAlerts } from '@/lib/hooks/useAlerts'
import { AlertFeed } from '@/components/common/AlertFeed'
import { AlertToastEmitter } from '@/components/common/AlertToastEmitter'

export function AlertSection() {
  const { projectId } = useProject()
  const { alerts } = useAlerts(projectId)

  return (
    <>
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-3">
          Alerts
        </h3>
        <AlertFeed alerts={alerts} />
      </div>
      <AlertToastEmitter projectId={projectId} />
    </>
  )
}
