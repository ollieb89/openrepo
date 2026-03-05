'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useProject } from '@/context/ProjectContext';
import { useTasks } from '@/lib/hooks/useTasks';
import { usePipeline } from '@/lib/hooks/usePipeline';
import { PipelineStrip } from '@/components/metrics/PipelineStrip';
import type { Task } from '@/lib/types';

/**
 * Pure function — encapsulates expand/collapse Set logic for task rows.
 * Exported for direct testing without rendering.
 *
 * Normal click (shiftKey=false):
 *   - If taskId already expanded -> collapse (clear set)
 *   - Otherwise -> clear all others, expand only taskId
 *
 * Shift click (shiftKey=true):
 *   - Toggle taskId without affecting other expanded rows
 */
export function getExpandedIds(
  prev: Set<string>,
  taskId: string,
  shiftKey: boolean
): Set<string> {
  const next = new Set(prev);
  if (shiftKey) {
    next.has(taskId) ? next.delete(taskId) : next.add(taskId);
  } else {
    if (next.has(taskId)) {
      next.clear();
    } else {
      next.clear();
      next.add(taskId);
    }
  }
  return next;
}

/**
 * Determines whether a task should be auto-expanded on mount.
 * Auto-expand: failed, escalating, or in_progress/starting/testing where L2 elapsed > 60s.
 */
function shouldAutoExpand(task: Task): boolean {
  if (task.status === 'failed' || task.status === 'escalating') return true;
  if (
    task.status === 'in_progress' ||
    task.status === 'starting' ||
    task.status === 'testing'
  ) {
    const metadata = (task as any).metadata as Record<string, any> | undefined;
    const routedAt = metadata?.routed_at;
    if (routedAt !== undefined) {
      const elapsedSeconds = Date.now() / 1000 - routedAt;
      if (elapsedSeconds > 60) return true;
    }
  }
  return false;
}

/** Inner component — calls usePipeline unconditionally (no conditional hook). */
function ExpandedPipelineRow({
  projectId,
  task,
}: {
  projectId: string;
  task: Task;
}) {
  const { pipelines, isLoading } = usePipeline(projectId, task.id);
  const pipeline = pipelines[0] ?? null;
  const metadata = (task as any).metadata as Record<string, any> | undefined;

  const failureReason = metadata?.failure_reason as string | undefined;
  const startedAt = metadata?.routed_at as number | undefined;
  const retries = (metadata?.retries as number | undefined) ?? 0;

  const elapsedLabel = (() => {
    if (!startedAt) return null;
    const sec = Math.round(Date.now() / 1000 - startedAt);
    if (sec < 60) return `${sec}s`;
    const mins = Math.floor(sec / 60);
    return `${mins}m ${sec % 60}s`;
  })();

  const currentStage =
    pipeline?.stages?.find(
      (s: { status: string }) => s.status === 'active' || s.status === 'failed'
    )?.name ?? null;

  return (
    <div className="px-2 pb-2 pt-1 bg-gray-50 dark:bg-gray-700/40 rounded-b-lg">
      {isLoading ? (
        <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded animate-pulse w-full" />
      ) : pipeline ? (
        <PipelineStrip stages={pipeline.stages} compact={false} />
      ) : (
        <p className="text-xs text-gray-400 italic">No pipeline data</p>
      )}

      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1.5 text-xs text-gray-500 dark:text-gray-400">
        {elapsedLabel && (
          <span>
            Elapsed:{' '}
            <span className="font-medium text-gray-700 dark:text-gray-300">
              {elapsedLabel}
            </span>
          </span>
        )}
        {currentStage && (
          <span>
            Stage:{' '}
            <span className="font-medium text-gray-700 dark:text-gray-300">
              {currentStage}
            </span>
          </span>
        )}
        {retries > 0 && (
          <span className="text-amber-600 dark:text-amber-400">
            Attempt #{retries + 1}
          </span>
        )}
      </div>

      {failureReason && (
        <p
          className="mt-1 text-xs text-red-600 dark:text-red-400 truncate"
          title={failureReason}
        >
          {failureReason}
        </p>
      )}

      <div className="flex items-center gap-2 mt-1.5">
        <Link
          href={`/tasks?open=${task.id}`}
          className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
          onClick={e => e.stopPropagation()}
        >
          View logs
        </Link>
        <button
          type="button"
          className="text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
          onClick={e => {
            e.stopPropagation();
            console.log('[TaskPulse] Retry stub — task:', task.id);
          }}
        >
          Retry
        </button>
      </div>
    </div>
  );
}

export default function TaskPulse() {
  const { projectId } = useProject();
  const { tasks, isLoading } = useTasks(projectId);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  // Visible tasks: active + failed (operators need to see failures)
  const visibleTasks = tasks
    .filter(
      t =>
        t.status === 'in_progress' ||
        t.status === 'starting' ||
        t.status === 'testing' ||
        t.status === 'failed' ||
        t.status === 'escalating'
    )
    .slice(0, 5);

  const pendingCount = tasks.filter(t => t.status === 'pending').length;

  // Auto-expand on mount and when visible task IDs change
  const taskIdKey = visibleTasks.map(t => t.id).join(',');
  useEffect(() => {
    const autoIds = visibleTasks.filter(shouldAutoExpand).map(t => t.id);
    if (autoIds.length > 0) {
      setExpandedIds(prev => {
        const next = new Set(prev);
        autoIds.forEach(id => next.add(id));
        return next;
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [taskIdKey]);

  function handleRowClick(taskId: string, shiftKey: boolean) {
    setExpandedIds(prev => getExpandedIds(prev, taskId, shiftKey));
  }

  function handleRowKeyDown(
    e: React.KeyboardEvent<HTMLDivElement>,
    taskId: string
  ) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleRowClick(taskId, e.shiftKey);
    }
  }

  function dotColor(status: Task['status']): string {
    if (status === 'failed' || status === 'escalating') return 'bg-red-500';
    return 'bg-green-500';
  }

  function pingColor(status: Task['status']): string {
    if (status === 'failed' || status === 'escalating') return 'bg-red-400';
    return 'bg-green-400';
  }

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

      <div className="space-y-1 flex-1">
        {isLoading && (
          <p className="text-xs text-gray-400 text-center py-4">Loading…</p>
        )}
        {!isLoading && visibleTasks.length === 0 && (
          <p className="text-xs text-gray-400 text-center py-4">No active tasks</p>
        )}
        {visibleTasks.map(task => {
          const isExpanded = expandedIds.has(task.id);
          return (
            <div key={task.id}>
              <div
                role="button"
                tabIndex={0}
                onClick={e => handleRowClick(task.id, e.shiftKey)}
                onKeyDown={e => handleRowKeyDown(e, task.id)}
                className={[
                  'flex items-center gap-3 text-xs rounded-lg px-2 py-1.5 transition-colors cursor-pointer select-none',
                  'hover:bg-gray-50 dark:hover:bg-gray-700/50',
                  isExpanded
                    ? 'bg-gray-50 dark:bg-gray-700/40 rounded-b-none'
                    : '',
                ].join(' ')}
                aria-expanded={isExpanded}
              >
                <span className="relative flex-shrink-0" aria-hidden="true">
                  <span
                    className={`animate-ping absolute inline-flex h-2 w-2 rounded-full ${pingColor(task.status)} opacity-75`}
                  />
                  <span
                    className={`relative inline-flex rounded-full h-2 w-2 ${dotColor(task.status)}`}
                  />
                </span>
                <span className="font-mono text-gray-500 flex-shrink-0 w-24 truncate">
                  {task.id}
                </span>
                <span className="text-gray-700 dark:text-gray-300 truncate flex-1">
                  {task.skill_hint || task.status}
                </span>
                <span
                  className={`text-gray-400 flex-shrink-0 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                  aria-hidden="true"
                >
                  &#8964;
                </span>
              </div>

              {isExpanded && projectId && (
                <ExpandedPipelineRow projectId={projectId} task={task} />
              )}
            </div>
          );
        })}
      </div>

      <Link href="/tasks" className="text-xs text-blue-600 hover:underline mt-auto">
        View all tasks -&gt;
      </Link>
    </div>
  );
}
