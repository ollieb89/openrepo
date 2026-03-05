'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { EventType, OrchestratorEvent, TaskOutputPayload } from '@/lib/types/events';
import { suffixOverlapMerge } from '@/lib/logViewer-utils';

export interface LogEntry {
  line: string;
  stream: 'stdout' | 'stderr';
  timestamp: number;
}

interface LogViewerProps {
  taskId?: string;
  /** @deprecated Use taskId instead */
  containerId?: string;
  /** @deprecated Use supplementalLines instead */
  staticLines?: LogEntry[];
  /** When false, SSE is not opened. Default: true */
  isActive?: boolean;
  /** Hide the built-in header. Default: false */
  hideHeader?: boolean;
  /** Activity log entries to merge into the live buffer on task completion (Effect C). */
  supplementalLines?: LogEntry[];
}

const MAX_LOG_ENTRIES = 1000;

export default function LogViewer({ taskId, containerId, staticLines, isActive = true, hideHeader = false, supplementalLines }: LogViewerProps) {
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
  const prevTaskIdRef = useRef<string | undefined>(undefined);
  const mergedForTaskIdRef = useRef<string | undefined>(undefined);

  const connectToEventSource = useCallback(() => {
    if (!isMountedRef.current) return;
    if (!isActive) return;  // defensive guard

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
      setError('Connection lost. Reconnecting...');
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
  }, [effectiveTaskId, isActive]);

  // Mount/unmount lifecycle — isMountedRef management and final SSE cleanup
  useEffect(() => {
    isMountedRef.current = true;
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
  }, []);

  // Effect A: log lifecycle — clears buffer only on real task switch
  // INVARIANT: never clears logs due to isActive changes
  useEffect(() => {
    const prevId = prevTaskIdRef.current;
    prevTaskIdRef.current = effectiveTaskId;

    if (prevId === effectiveTaskId) return; // same id — no-op

    if (prevId === undefined && effectiveTaskId !== undefined) {
      // Initialize: first mount or resuming from undefined — start fresh
      setLogs([]);
      setError(null);
      reconnectDelayRef.current = 1000;
    } else if (prevId !== undefined && effectiveTaskId === undefined) {
      // Task removed/hidden: PRESERVE BUFFER — stop streaming but do not erase
      setConnected(false);
      setError(null);
    } else if (prevId !== effectiveTaskId && effectiveTaskId !== undefined) {
      // Real task switch: clear buffer and start fresh
      setLogs([]);
      setError(null);
      reconnectDelayRef.current = 1000;
    }
  }, [effectiveTaskId]);

  // Effect B: SSE lifecycle — connects/disconnects stream, never touches logs
  useEffect(() => {
    if (!effectiveTaskId || isActive === false) {
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      setConnected(false);
      return;
    }

    connectToEventSource();

    return () => {
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, [effectiveTaskId, isActive, connectToEventSource]);

  // Effect C: supplemental merge — runs at most once per task completion
  // Appends any activity_log tail entries not already in the live buffer.
  useEffect(() => {
    if (
      !isActive &&
      supplementalLines &&
      supplementalLines.length > 0 &&
      effectiveTaskId &&
      effectiveTaskId !== mergedForTaskIdRef.current
    ) {
      mergedForTaskIdRef.current = effectiveTaskId;
      setLogs(prev => suffixOverlapMerge(prev, supplementalLines));
    }
  }, [isActive, supplementalLines, effectiveTaskId]);

  const displayLines = (!isActive && staticLines) ? staticLines : logs;

  useEffect(() => {
    if (autoScrollRef.current && logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [displayLines]);

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
          {isActive && (
            <button
              onClick={() => setLogs([])}
              className="px-3 py-1 text-xs bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded text-gray-600 dark:text-gray-300"
            >
              Clear
            </button>
          )}
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
