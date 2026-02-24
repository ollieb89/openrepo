'use client';

import type { Task } from '@/lib/types';
import StatusBadge from '@/components/common/StatusBadge';

function timeAgo(timestamp: number): string {
  const seconds = Math.floor((Date.now() / 1000) - timestamp);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

interface TaskCardProps {
  task: Task;
  onClick: (task: Task) => void;
}

export default function TaskCard({ task, onClick }: TaskCardProps) {
  const lastActivity = task.activity_log[task.activity_log.length - 1];

  return (
    <div
      onClick={() => onClick(task)}
      className="p-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-sm cursor-pointer hover:shadow-md hover:border-gray-300 dark:hover:border-gray-600 transition-all"
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <span className="text-xs font-mono text-gray-500 dark:text-gray-400 truncate">
          {task.id}
        </span>
        <StatusBadge status={task.status} />
      </div>

      {task.skill_hint && (
        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 mb-2">
          {task.skill_hint}
        </span>
      )}

      {lastActivity && (
        <p className="text-xs text-gray-600 dark:text-gray-400 line-clamp-2 mb-2">
          {lastActivity.entry}
        </p>
      )}

      <div className="flex items-center justify-between text-xs text-gray-400 dark:text-gray-500">
        <span>{timeAgo(task.created_at)}</span>
        <span>{task.activity_log.length} events</span>
      </div>
    </div>
  );
}
