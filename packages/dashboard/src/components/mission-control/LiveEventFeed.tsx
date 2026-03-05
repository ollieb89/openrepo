'use client';

import { useEffect, useRef, useState } from 'react';
import { useProject } from '@/context/ProjectContext';
import { useLiveEvents, type LiveEventStatus } from '@/lib/hooks/useLiveEvents';

const TYPE_COLORS: Record<string, string> = {
  task_created: 'bg-blue-500',
  task_started: 'bg-amber-500',
  task_completed: 'bg-green-500',
  task_failed: 'bg-red-500',
  task_escalated: 'bg-purple-500',
  container_started: 'bg-cyan-500',
  container_stopped: 'bg-gray-400',
};

const STATUS_PILL: Record<LiveEventStatus, { label: string; className: string }> = {
  connecting: {
    label: 'connecting…',
    className: 'border-gray-200 dark:border-gray-600 text-gray-500',
  },
  live: {
    label: 'live',
    className:
      'bg-green-100 border-green-300 text-green-700 dark:bg-green-900 dark:border-green-700 dark:text-green-300',
  },
  reconnecting: {
    label: 'reconnecting…',
    className:
      'bg-amber-100 border-amber-300 text-amber-700 dark:bg-amber-900 dark:border-amber-700 dark:text-amber-300',
  },
  offline: {
    label: 'offline (polling)',
    className:
      'bg-red-100 border-red-300 text-red-700 dark:bg-red-900 dark:border-red-700 dark:text-red-300',
  },
};

function relativeTime(ms: number): string {
  const diff = Math.floor((Date.now() - ms) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  return `${Math.floor(diff / 3600)}h ago`;
}

export default function LiveEventFeed() {
  const { projectId } = useProject();
  const { events, status } = useLiveEvents(projectId);
  const [paused, setPaused] = useState(false);
  const [filterTasks, setFilterTasks] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom unless paused
  useEffect(() => {
    if (!paused && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [events, paused]);

  const displayed = filterTasks ? events.filter((e) => e.type.startsWith('task_')) : events;
  const pill = STATUS_PILL[status];

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 flex flex-col gap-3 min-h-0">
      <div className="flex items-center justify-between flex-shrink-0">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
          Live Event Feed
        </h3>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setFilterTasks((f) => !f)}
            className={`text-xs px-2 py-0.5 rounded-full border transition-colors ${
              filterTasks
                ? 'bg-blue-100 border-blue-300 text-blue-700 dark:bg-blue-900 dark:border-blue-700 dark:text-blue-300'
                : 'border-gray-200 dark:border-gray-600 text-gray-500 hover:border-gray-300'
            }`}
          >
            tasks
          </button>
          <button
            onClick={() => setPaused((p) => !p)}
            className={`text-xs px-2 py-0.5 rounded-full border transition-colors ${
              paused
                ? 'bg-amber-100 border-amber-300 text-amber-700 dark:bg-amber-900 dark:border-amber-700 dark:text-amber-300'
                : 'border-gray-200 dark:border-gray-600 text-gray-500 hover:border-gray-300'
            }`}
          >
            {paused ? 'paused' : 'scroll'}
          </button>
          {/* Connection status pill */}
          <span className={`text-xs px-2 py-0.5 rounded-full border ${pill.className}`}>
            {pill.label}
          </span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto space-y-1 min-h-0 max-h-48">
        {displayed.length === 0 && (
          <p className="text-xs text-gray-400 text-center py-4">
            {status === 'offline' ? 'Offline — waiting for events…' : 'Waiting for events…'}
          </p>
        )}
        {displayed.map((ev) => (
          <div key={ev.id} className="flex items-start gap-2 text-xs">
            <span
              className={`mt-1 w-1.5 h-1.5 rounded-full flex-shrink-0 ${TYPE_COLORS[ev.type] ?? 'bg-gray-400'}`}
              role="img"
              aria-label={ev.type}
            />
            <span className="text-gray-700 dark:text-gray-300 flex-1 truncate">
              {ev.task_id && (
                <span className="font-mono text-gray-500">{ev.task_id} </span>
              )}
              {ev.type.replace(/_/g, ' ')}
              {ev.message ? ` — ${ev.message}` : ''}
            </span>
            <span className="text-gray-400 flex-shrink-0">{relativeTime(ev.rawAt)}</span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
