'use client';

import { useState, useMemo } from 'react';
import type { TaskStatus } from '@/lib/types';
import { useTasks } from '@/lib/hooks/useTasks';
import { useProject } from '@/context/ProjectContext';
import TaskCard from './TaskCard';
import TaskTerminalPanel from './TaskTerminalPanel';
import PipelineView from './PipelineView';
import StatusBadge from '@/components/common/StatusBadge';
import Card from '@/components/common/Card';

const STATUS_COLUMNS: { status: TaskStatus; label: string }[] = [
  { status: 'pending', label: 'Pending' },
  { status: 'in_progress', label: 'In Progress' },
  { status: 'testing', label: 'Testing' },
  { status: 'completed', label: 'Completed' },
  { status: 'failed', label: 'Failed' },
];

function getColumnTasks(tasks: ReturnType<typeof useTasks>['tasks'], status: TaskStatus) {
  return tasks.filter(t =>
    status === 'in_progress'
      ? t.status === 'in_progress' || t.status === 'starting'
      : status === 'failed'
        ? t.status === 'failed' || t.status === 'rejected'
        : t.status === status
  );
}

export default function TaskBoard() {
  const { projectId } = useProject();
  const { tasks, isLoading } = useTasks(projectId);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<TaskStatus | null>(null);

  const selectedTask = selectedTaskId
    ? tasks.find(t => t.id === selectedTaskId) ?? null
    : null;

  const columnTasksMap = useMemo(
    () => new Map(STATUS_COLUMNS.map(col => [col.status, getColumnTasks(tasks, col.status)])),
    [tasks]
  );

  function handleTaskClick(taskId: string) {
    setSelectedTaskId(taskId);
    setFilterStatus(null);
  }

  function handleStatClick(status: TaskStatus) {
    setFilterStatus(prev => (prev === status ? null : status));
  }

  // Guard: no project selected
  if (!projectId) {
    return (
      <Card className="text-center py-12">
        <div className="px-4">
          <svg className="mx-auto h-12 w-12 text-gray-400 dark:text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 9.776c.112-.017.227-.026.344-.026h15.812c.117 0 .232.009.344.026m-16.5 0a2.25 2.25 0 00-1.883 2.542l.857 6a2.25 2.25 0 002.227 1.932H19.05a2.25 2.25 0 002.227-1.932l.857-6a2.25 2.25 0 00-1.883-2.542m-16.5 0V6A2.25 2.25 0 016 3.75h3.879a1.5 1.5 0 011.06.44l2.122 2.12a1.5 1.5 0 001.06.44H18A2.25 2.25 0 0120.25 9v.776" />
          </svg>
          <h3 className="mt-3 text-sm font-semibold text-gray-900 dark:text-white">No project selected</h3>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Select a project from the dropdown in the header to view tasks.
          </p>
        </div>
      </Card>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500 dark:text-gray-400">
        Loading tasks...
      </div>
    );
  }

  if (tasks.length === 0) {
    return (
      <Card className="text-center py-12">
        <div className="px-4">
          <svg className="mx-auto h-12 w-12 text-gray-400 dark:text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15a2.25 2.25 0 012.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25zM6.75 12h.008v.008H6.75V12zm0 3h.008v.008H6.75V15zm0 3h.008v.008H6.75V18z" />
          </svg>
          <h3 className="mt-3 text-sm font-semibold text-gray-900 dark:text-white">No tasks</h3>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            No L3 tasks found for this project. Tasks appear when L2 delegates work to L3 specialists.
          </p>
        </div>
      </Card>
    );
  }

  return (
    <div className="flex flex-col h-full gap-4">
      {/* Stats summary row */}
      <div className="grid grid-cols-5 gap-3 flex-shrink-0">
        {STATUS_COLUMNS.map(col => {
          const count = (columnTasksMap.get(col.status) ?? []).length;
          const isActive = filterStatus === col.status;
          return (
            <button
              key={col.status}
              onClick={() => handleStatClick(col.status)}
              aria-label={`Filter by ${col.label}${isActive ? ' (active)' : ''}`}
              aria-pressed={isActive}
              className={`p-3 rounded-lg border text-center transition-all ${
                isActive
                  ? 'bg-blue-50 dark:bg-blue-900/30 border-blue-300 dark:border-blue-700 ring-1 ring-blue-400'
                  : 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
              }`}
            >
              <div className="text-2xl font-bold text-gray-900 dark:text-white mb-1">{count}</div>
              <StatusBadge status={col.status} />
            </button>
          );
        })}
      </div>

      {/* Pipeline banner — shown when a task is selected */}
      {selectedTask && (
        <div className="flex-shrink-0">
          <PipelineView status={selectedTask.status} />
        </div>
      )}

      {/* Kanban + terminal panel */}
      <div className="flex gap-4 flex-1 min-h-0">
        <div className="flex-1 flex gap-4 overflow-x-auto pb-4">
          {STATUS_COLUMNS.map(col => {
            const colTasks = columnTasksMap.get(col.status) ?? [];
            const isDimmed = filterStatus !== null && filterStatus !== col.status;

            return (
              <div
                key={col.status}
                className={`flex-shrink-0 w-64 transition-opacity ${isDimmed ? 'opacity-40' : 'opacity-100'}`}
              >
                <div className="flex items-center gap-2 mb-3 px-1">
                  <StatusBadge status={col.status} />
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    {colTasks.length}
                  </span>
                </div>
                <div className="space-y-2">
                  {colTasks.map(task => (
                    <TaskCard
                      key={task.id}
                      task={task}
                      onClick={() => handleTaskClick(task.id)}
                    />
                  ))}
                </div>
              </div>
            );
          })}
        </div>

        {selectedTask && (
          <TaskTerminalPanel
            task={selectedTask}
            onClose={() => setSelectedTaskId(null)}
          />
        )}
      </div>
    </div>
  );
}
