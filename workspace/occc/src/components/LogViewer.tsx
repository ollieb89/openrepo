'use client';

import { useEffect, useRef, useState } from 'react';

interface LogEntry {
  line: string;
  timestamp: number;
}

interface LogViewerProps {
  containerId?: string;
}

export default function LogViewer({ containerId }: LogViewerProps) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const logContainerRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!containerId) {
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
    setConnected(true);

    const eventSource = new EventSource(`/api/swarm/stream?containerId=${containerId}`);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      setConnected(true);
      setError(null);
    };

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setLogs(prev => [...prev, data]);
      } catch (err) {
        console.error('Error parsing log data:', err);
      }
    };

    eventSource.onerror = () => {
      setConnected(false);
      setError('Connection to log stream lost');
      eventSource.close();
    };

    return () => {
      eventSource.close();
      eventSourceRef.current = null;
    };
  }, [containerId]);

  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs]);

  if (!containerId) {
    return (
      <div className="border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 p-8 text-center text-gray-500 dark:text-gray-400">
        <p>Select a container to view its logs</p>
      </div>
    );
  }

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800">
      <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
        <div>
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Container Logs</h2>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {connected ? (
              <span className="text-green-600 dark:text-green-400">Connected</span>
            ) : (
              <span className="text-gray-400">Disconnected</span>
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
        className="h-96 overflow-y-auto p-4 bg-gray-900 text-gray-100 font-mono text-xs"
      >
        {logs.length === 0 ? (
          <div className="text-gray-500">Waiting for logs...</div>
        ) : (
          logs.map((log, index) => (
            <div key={index} className="mb-0.5">
              <span className="text-gray-500">
                [{new Date(log.timestamp).toLocaleTimeString()}]
              </span>{' '}
              {log.line}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
