'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { EventType, OrchestratorEvent, TaskOutputPayload } from '@/lib/types/events';

interface LogEntry {
  line: string;
  stream: 'stdout' | 'stderr';
  timestamp: number;
}

interface LogViewerProps {
  taskId?: string;
  /** @deprecated Use taskId instead */
  containerId?: string;
}

const MAX_LOG_ENTRIES = 1000;

export default function LogViewer({ taskId, containerId }: LogViewerProps) {
  // Prefer taskId; fall back to containerId for backward compat
  const effectiveTaskId = taskId || containerId;

  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const logContainerRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectDelayRef = useRef<number>(1000);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isMountedRef = useRef(true);

  const connectToEventSource = useCallback(() => {
    if (!isMountedRef.current) return;

    // Close existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    const eventSource = new EventSource('/api/events');
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      if (!isMountedRef.current) return;
      setConnected(true);
      setError(null);
      reconnectDelayRef.current = 1000; // Reset backoff on successful connection
    };

    eventSource.onmessage = (event) => {
      if (!isMountedRef.current) return;
      try {
        const parsed: OrchestratorEvent = JSON.parse(event.data);

        // Filter: only task.output events for this task
        if (parsed.type !== EventType.TASK_OUTPUT) return;
        if (parsed.task_id !== effectiveTaskId) return;

        const outputPayload = parsed.payload as TaskOutputPayload | undefined;
        if (!outputPayload) return;

        const newEntry: LogEntry = {
          line: outputPayload.line,
          stream: outputPayload.stream || 'stdout',
          timestamp: parsed.timestamp,
        };

        setLogs(prev => {
          const next = [...prev, newEntry];
          return next.length > MAX_LOG_ENTRIES ? next.slice(-MAX_LOG_ENTRIES) : next;
        });
      } catch (err) {
        console.error('Error parsing event data:', err);
      }
    };

    eventSource.onerror = () => {
      if (!isMountedRef.current) return;
      setConnected(false);
      eventSource.close();
      eventSourceRef.current = null;

      const delay = reconnectDelayRef.current;
      reconnectDelayRef.current = Math.min(delay * 2, 30_000);

      reconnectTimerRef.current = setTimeout(() => {
        if (isMountedRef.current) {
          connectToEventSource();
        }
      }, delay);
    };
  }, [effectiveTaskId]);

  useEffect(() => {
    isMountedRef.current = true;

    if (!effectiveTaskId) {
      setLogs([]);
      setConnected(false);
      setError(null);
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      return;
    }

    setLogs([]);
    setError(null);
    reconnectDelayRef.current = 1000;
    connectToEventSource();

    return () => {
      isMountedRef.current = false;
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, [effectiveTaskId, connectToEventSource]);

  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs]);

  if (!effectiveTaskId) {
    return (
      <div className="border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 p-8 text-center text-gray-500 dark:text-gray-400">
        <p>Select a task to view its output</p>
      </div>
    );
  }

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800">
      <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
        <div>
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Task Output</h2>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {connected ? (
              <span className="text-green-600 dark:text-green-400">Connected</span>
            ) : (
              <span className="text-gray-400">Reconnecting...</span>
            )} &middot; {logs.length} lines
          </p>
        </div>
        <button
          onClick={() => setLogs([])}
          className="px-3 py-1 text-xs bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded text-gray-600 dark:text-gray-300"
        >
          Clear
        </button>
      </div>

      {error && (
        <div className="p-3 bg-red-50 dark:bg-red-900/20 border-b border-red-200 dark:border-red-800 text-sm text-red-700 dark:text-red-400">
          {error}
        </div>
      )}

      <div
        ref={logContainerRef}
        className="h-96 overflow-y-auto p-4 bg-gray-900 font-mono text-xs"
      >
        {logs.length === 0 ? (
          <div className="text-gray-500">Waiting for output...</div>
        ) : (
          logs.map((log, index) => (
            <div key={index} className="mb-0.5">
              <span className="text-gray-500">
                [{new Date(log.timestamp).toLocaleTimeString()}]
              </span>{' '}
              <span className={log.stream === 'stderr' ? 'text-red-400' : 'text-gray-100'}>
                {log.line}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
