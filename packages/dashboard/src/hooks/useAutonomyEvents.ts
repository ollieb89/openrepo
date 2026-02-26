'use client';

import { useState, useEffect, useCallback } from 'react';
import type { AutonomyEvent, AutonomyState, CourseCorrection } from '@/lib/types/autonomy';

interface UseAutonomyEventsOptions {
  taskId?: string;
  eventType?: string;
}

export function useAutonomyEvents(options: UseAutonomyEventsOptions = {}) {
  const { taskId, eventType } = options;
  const [events, setEvents] = useState<AutonomyEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    // Build WebSocket URL with optional task filter
    const params = new URLSearchParams();
    if (taskId) params.append('task', taskId);
    
    const wsUrl = `ws://localhost:8080/events?${params.toString()}`;
    let ws: WebSocket | null = null;
    let reconnectTimeout: NodeJS.Timeout;

    const connect = () => {
      try {
        ws = new WebSocket(wsUrl);
        
        ws.onopen = () => {
          setIsConnected(true);
          setError(null);
        };
        
        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data) as AutonomyEvent;
            
            const evType = data.event_type ?? data.type;
            if (eventType && evType !== eventType) {
              return;
            }
            
            setEvents(prev => [...prev, data]);
          } catch (err) {
            console.error('Failed to parse autonomy event:', err);
          }
        };
        
        ws.onclose = () => {
          setIsConnected(false);
          // Attempt to reconnect after 3 seconds
          reconnectTimeout = setTimeout(connect, 3000);
        };
        
        ws.onerror = (err) => {
          setError(new Error('WebSocket error occurred'));
          setIsConnected(false);
        };
      } catch (err) {
        setError(err instanceof Error ? err : new Error('Failed to connect'));
      }
    };

    connect();

    return () => {
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (ws) {
        ws.onclose = null; // Prevent reconnection on manual close
        ws.close();
      }
    };
  }, [taskId, eventType]);

  const clearEvents = useCallback(() => {
    setEvents([]);
  }, []);

  return { events, isConnected, error, clearEvents };
}

export function useAutonomyState(taskId: string) {
  const [state, setState] = useState<AutonomyState | null>(null);
  const { events, isConnected } = useAutonomyEvents({ taskId });

  useEffect(() => {
    const getEvType = (e: AutonomyEvent & { event_type?: string }) =>
      (e as { event_type?: string; type?: string }).event_type ?? (e as { type?: string }).type;
    const stateEvents = events.filter(e => getEvType(e) === 'autonomy.state_changed');
    if (stateEvents.length > 0) {
      const latest = stateEvents[stateEvents.length - 1];
      setState(latest.payload.state as AutonomyState);
    }
  }, [events]);

  return { state, isConnected };
}

export function useCourseCorrections(taskId: string) {
  const [corrections, setCorrections] = useState<CourseCorrection[]>([]);
  const { events } = useAutonomyEvents({ taskId, eventType: 'autonomy.course_correction' });

  useEffect(() => {
    const getEvType = (e: AutonomyEvent & { event_type?: string }) =>
      (e as { event_type?: string; type?: string }).event_type ?? (e as { type?: string }).type;
    const courseCorrections = events
      .filter(e => getEvType(e) === 'autonomy.course_correction')
      .map(e => ({
        timestamp: e.timestamp,
        failed_step: e.payload.failed_step,
        recovery_steps: e.payload.recovery_steps,
      }));
    
    setCorrections(courseCorrections);
  }, [events]);

  return corrections;
}

export default useAutonomyEvents;
