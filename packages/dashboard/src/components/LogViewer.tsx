'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { EventType, OrchestratorEvent, TaskOutputPayload } from '@/lib/types/events';

export interface LogEntry {
  line: string;
  stream: 'stdout' | 'stderr';
  timestamp: number;
}

interface LogViewerProps {
  taskId?: string;
  /** @deprecated Use taskId instead */
  containerId?: string;
  /** Pre-built log lines for completed/failed tasks (skips SSE when isActive=false) */
  staticLines?: LogEntry[];
  /** When false and staticLines provided, SSE is not opened. Default: true */
  isActive?: boolean;
  /** Hide the built-in header (title, connected status, clear button). Default: false */
  hideHeader?: boolean;
}

const MAX_LOG_ENTRIES = 1000;

export default function LogViewer({ taskId, containerId, staticLines, isActive = true, hideHeader = false }: LogViewerProps) {
  // Prefer taskId; fall back to containerId for backward compat
  const effectiveTaskId = taskId || containerId;

  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [autoScrollPaused, setAutoScrollPaused] = useState(false);
  const logContainerRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectDelayRef = useRef<number>(1000);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isMountedRef = useRef(true);
  const autoScrollRef = useRef(true);

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

    if (isActive !== false) {
      connectToEventSource();
    }

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
  }, [effectiveTaskId, connectToEventSource, isActive]);

  useEffect(() => {
    if (autoScrollRef.current && logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs]);

  const handleScroll = useCallback(() => {
    const el = logContainerRef.current;
    if (!el) return;
    const atBottom = el.scrollTop + el.clientHeight >= el.scrollHeight - 20;
    if (atBottom) {
      autoScrollRef.current = true;
      setAutoScrollPaused(false);
    } else {
      autoScrollRef.current = false;
      setAutoScrollPaused(true);
    }
  }, []);

  const resumeScroll = useCallback(() => {
    autoScrollRef.current = true;
    setAutoScrollPaused(false);
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, []);

  const displayLines = (!isActive && staticLines) ? staticLines : logs;

  if (!effectiveTaskId && !staticLines) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-950 text-gray-600 text-xs font-mono">
        Select a task to view output
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-gray-950 font-mono text-xs">
      {!hideHeader && (
        <div className="px-4 py-2 border-b border-gray-700 flex justify-between items-center flex-shrink-0 bg-gray-900">
          <div>
            <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Task Output</h2>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {connected ? (
                <span className="text-green-600 dark:text-green-400">Connected</span>
              ) : (
                <span className="text-gray-400">Reconnecting...</span>
              )} &middot; {displayLines.length} lines
            </p>
          </div>
          <button
            onClick={() => setLogs([])}
            className="px-3 py-1 text-xs bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded text-gray-600 dark:text-gray-300"
          >
            Clear
          </button>
        </div>
      )}

      <div className="relative flex-1 overflow-hidden">
        <div
          ref={logContainerRef}
          onScroll={handleScroll}
          className="h-full overflow-y-auto p-3"
        >
          {displayLines.length === 0 ? (
            <div className="text-gray-600">
              {isActive === false ? 'No output recorded' : 'Waiting for output...'}
            </div>
          ) : (
            displayLines.map((log, index) => (
              <div key={index} className="mb-0.5 leading-relaxed">
                <span className="text-gray-600">
                  [{new Date(log.timestamp).toLocaleTimeString()}]
                </span>{' '}
                <span className={log.stream === 'stderr' ? 'text-red-400' : 'text-gray-100'}>
                  {log.line}
                </span>
              </div>
            ))
          )}
        </div>

        {autoScrollPaused && (
          <div className="absolute bottom-3 right-3">
            <button
              onClick={resumeScroll}
              className="px-3 py-1 bg-gray-700 hover:bg-gray-600 text-gray-200 rounded-full text-xs border border-gray-600"
            >
              ↓ scroll to resume
            </button>
          </div>
        )}
      </div>

      {error && (
        <div className="px-3 py-1 bg-red-900/30 border-t border-red-800 text-xs text-red-400 flex-shrink-0">
          {error}
        </div>
      )}
    </div>
  );
}
