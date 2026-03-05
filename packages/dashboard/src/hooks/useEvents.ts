'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import type { OrchestratorEvent } from '@/lib/types/events';

export function useEvents(projectId?: string) {
  const [lastEvent, setLastEvent] = useState<OrchestratorEvent | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  const connect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const url = projectId ? `/api/events?project=${projectId}` : '/api/events';
    const es = new EventSource(url);

    es.addEventListener('connected', () => {
      setIsConnected(true);
      setError(null);
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

    es.addEventListener('error', (e) => {
      console.warn('[useEvents] SSE connection unavailable — orchestrator may not be running');
      setIsConnected(false);
      setError('Connection to event bridge failed');
    });

    eventSourceRef.current = es;
  }, [projectId]);

  useEffect(() => {
    connect();
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [connect]);

  return { lastEvent, isConnected, error, reconnect: connect };
}
