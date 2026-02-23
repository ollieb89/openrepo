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

    // Create EventSource for Server-Sent Events
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

  // Auto-scroll to bottom
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs]);

  const clearLogs = () => {
    setLogs([]);
  };

  if (!containerId) {
    return (
      <div className="border rounded-lg p-8 text-center text-gray-500">
        <p>Select a container to view its logs</p>
      </div>
    );
  }

  return (
    <div className="border rounded-lg">
      <div className="p-4 border-b flex justify-between items-center">
        <div>
          <h2 className="text-lg font-semibold">Container Logs</h2>
          <p className="text-sm text-gray-600">
            {connected ? 'Connected' : 'Disconnected'} • {logs.length} lines
          </p>
        </div>
        <button
          onClick={clearLogs}
          className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded"
        >
          Clear
        </button>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border-b text-red-700">
          {error}
        </div>
      )}

      <div
        ref={logContainerRef}
        className="h-96 overflow-y-auto p-4 bg-gray-900 text-gray-100 font-mono text-sm"
      >
        {logs.length === 0 ? (
          <div className="text-gray-500">Waiting for logs...</div>
        ) : (
          logs.map((log, index) => (
            <div key={index} className="mb-1">
              <span className="text-gray-400">
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
