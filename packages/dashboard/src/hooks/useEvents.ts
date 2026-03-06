'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import type { OrchestratorEvent } from '@/lib/types/events';

export function useEvents(projectId?: string) {
  const [lastEvent, setLastEvent] = useState<OrchestratorEvent | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [status, setStatus] = useState<'connecting' | 'live' | 'offline'>('connecting');
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectDelayRef = useRef<number>(5000);

  const connect = useCallback(() => {
    // Cancel any pending reconnect timer
    if (reconnectTimerRef.current !== null) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    setStatus('connecting');
    const url = projectId ? `/api/events?project=${projectId}` : '/api/events';
    const es = new EventSource(url);

    es.addEventListener('connected', () => {
      setIsConnected(true);
      setStatus('live');
      setError(null);
      // Reset backoff on successful connection
      reconnectDelayRef.current = 5000;
    });

    es.addEventListener('message', (e) => {
      try {
        const event: OrchestratorEvent = JSON.parse(e.data);
        if (!projectId || event.project_id === projectId) {
          setLastEvent(event);
        }
      } catch (err) {
        console.error('Failed to parse event data', err);
      }
    });

    es.addEventListener('error', () => {
      console.warn('[useEvents] SSE connection unavailable — orchestrator may not be running');
      setIsConnected(false);
      setStatus('offline');
      setError('Connection to event bridge failed');

      // Close the current source to prevent browser's own rapid reconnect
      es.close();
      eventSourceRef.current = null;

      // Exponential backoff reconnect (cap at 60s)
      const delay = reconnectDelayRef.current;
      reconnectDelayRef.current = Math.min(delay * 2, 60000);

      reconnectTimerRef.current = setTimeout(() => {
        reconnectTimerRef.current = null;
        connect();
      }, delay);
    });

    eventSourceRef.current = es;
  }, [projectId]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimerRef.current !== null) {
        clearTimeout(reconnectTimerRef.current);
      }
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [connect]);

  return { lastEvent, isConnected, status, error, reconnect: connect };
}
