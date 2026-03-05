'use client';

import { useState, useEffect, useRef } from 'react';
import type { Task, TaskActivityEntry } from '@/lib/types';
import type { LogEntry } from '@/components/LogViewer';
import LogViewer from '@/components/LogViewer';
import StatusBadge from '@/components/common/StatusBadge';
import PipelineView from './PipelineView';

interface TaskTerminalPanelProps {
  task: Task;
  onClose: () => void;
}

type BannerState = 'none' | 'syncing' | 'stored' | 'empty';

const BANNER_TEXT: Record<Exclude<BannerState, 'none'>, string> = {
  syncing: 'Task completed — syncing final log…',
  stored: 'Task completed — showing stored log',
  empty: 'Task completed',
};

function activityToLogEntries(entries: TaskActivityEntry[]): LogEntry[] {
  return entries.map(e => ({
    line: e.entry,
    stream: 'stdout' as const,
    timestamp: e.timestamp * 1000, // activity_log uses Unix seconds; LogViewer expects ms
  }));
}

export default function TaskTerminalPanel({ task, onClose }: TaskTerminalPanelProps) {
  const isActive = task.status === 'in_progress' || task.status === 'starting';

  // Stable logTaskId — advances only when user selects a genuinely different task.
  // task.id is a stable primitive string even when the task object is replaced by polling.
  const [logTaskId, setLogTaskId] = useState(task.id);
  useEffect(() => { setLogTaskId(task.id); }, [task.id]);

  // Banner state: tracks completion transition
  const [bannerState, setBannerState] = useState<BannerState>('none');

  // Completion edge detection: true → false triggers 'syncing' flash
  const wasActiveRef = useRef(isActive);
  useEffect(() => {
    if (wasActiveRef.current && !isActive) {
      setBannerState('syncing');
    }
    wasActiveRef.current = isActive;
  }, [isActive]);

  // Deterministic banner — keyed on activity_log presence, not async callback
  useEffect(() => {
    if (!isActive) {
      setBannerState(task.activity_log.length > 0 ? 'stored' : 'empty');
    }
  }, [isActive, task.activity_log.length]);

  // supplementalLines: activity_log entries for LogViewer Effect C to merge
  const supplementalLines = isActive ? undefined : activityToLogEntries(task.activity_log);

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

      {/* Pipeline stage indicator */}
      <div className="flex-shrink-0">
        <PipelineView status={task.status} compact />
      </div>

      {/* Completion banner — non-blocking strip explaining source-of-truth transition */}
      {bannerState !== 'none' && (
        <div className="px-3 py-1 bg-gray-800 border-b border-gray-700 text-xs text-gray-500 flex-shrink-0 select-none">
          {BANNER_TEXT[bannerState]}
        </div>
      )}

      {/* Terminal body */}
      <div className="flex-1 overflow-hidden">
        <LogViewer
          taskId={logTaskId}
          isActive={isActive}
          supplementalLines={supplementalLines}
          hideHeader={true}
        />
      </div>
    </div>
  );
}
