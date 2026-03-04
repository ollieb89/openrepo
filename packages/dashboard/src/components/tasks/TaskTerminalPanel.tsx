'use client';

import type { Task, TaskActivityEntry } from '@/lib/types';
import type { LogEntry } from '@/components/LogViewer';
import LogViewer from '@/components/LogViewer';
import StatusBadge from '@/components/common/StatusBadge';

interface TaskTerminalPanelProps {
  task: Task;
  onClose: () => void;
}

function activityToLogEntries(entries: TaskActivityEntry[]): LogEntry[] {
  return entries.map(e => ({
    line: e.entry,
    stream: 'stdout' as const,
    timestamp: e.timestamp * 1000, // activity_log uses Unix seconds; LogViewer expects ms
  }));
}

export default function TaskTerminalPanel({ task, onClose }: TaskTerminalPanelProps) {
  const isActive = task.status === 'in_progress' || task.status === 'starting';
  const staticLines = isActive ? undefined : activityToLogEntries(task.activity_log);

  return (
    <div className="flex flex-col w-80 flex-shrink-0 border-l border-gray-800 bg-gray-950 h-full">
      {/* Compact header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-800 flex-shrink-0 bg-gray-900 gap-2">
        <span className="font-mono text-xs text-gray-400 truncate flex-1" title={task.id}>
          {task.id}
        </span>
        <StatusBadge status={task.status} />
        <button
          onClick={onClose}
          className="text-gray-500 hover:text-gray-300 ml-1 flex-shrink-0 leading-none text-base"
          aria-label="Close terminal panel"
        >
          ×
        </button>
      </div>

      {/* Terminal body */}
      <div className="flex-1 overflow-hidden">
        <LogViewer
          taskId={isActive ? task.id : undefined}
          staticLines={staticLines}
          isActive={isActive}
          hideHeader={true}
        />
      </div>
    </div>
  );
}
