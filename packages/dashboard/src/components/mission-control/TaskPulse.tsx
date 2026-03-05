'use client';

import Link from 'next/link';
import { useProject } from '@/context/ProjectContext';
import { useTasks } from '@/lib/hooks/useTasks';

export default function TaskPulse() {
  const { projectId } = useProject();
  const { tasks } = useTasks(projectId);

  const activeTasks = tasks
    .filter(
      t => t.status === 'in_progress' || t.status === 'starting' || t.status === 'testing'
    )
    .slice(0, 5);

  const pendingCount = tasks.filter(t => t.status === 'pending').length;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
          Task Pulse
        </h3>
        {pendingCount > 0 && (
          <span className="text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 px-2 py-0.5 rounded-full">
            +{pendingCount} pending
          </span>
        )}
      </div>

      <div className="space-y-2 flex-1">
        {activeTasks.length === 0 && (
          <p className="text-xs text-gray-400 text-center py-4">No active tasks</p>
        )}
        {activeTasks.map(task => (
          <Link
            key={task.id}
            href={`/tasks?open=${task.id}`}
            className="flex items-center gap-3 text-xs hover:bg-gray-50 dark:hover:bg-gray-700/50 rounded-lg px-2 py-1.5 transition-colors"
          >
            <span className="relative flex-shrink-0" aria-hidden="true">
              <span className="animate-ping absolute inline-flex h-2 w-2 rounded-full bg-green-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500" />
            </span>
            <span className="font-mono text-gray-500 flex-shrink-0 w-24 truncate">{task.id}</span>
            <span className="text-gray-700 dark:text-gray-300 truncate flex-1">
              {task.skill_hint || task.status}
            </span>
          </Link>
        ))}
      </div>

      <Link href="/tasks" className="text-xs text-blue-600 hover:underline mt-auto">
        View all tasks →
      </Link>
    </div>
  );
}
