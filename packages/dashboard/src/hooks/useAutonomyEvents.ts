'use client';

import { useState, useEffect, useCallback } from 'react';
import type { AutonomyEvent, AutonomyState, AutonomyStateChangedEvent, AutonomyCourseCorrectionEvent, CourseCorrection } from '@/lib/types/autonomy';
import { createWsClient, type ConnectionState } from '@/lib/ws-client';
import { wsUrl } from '@/lib/api-client';

interface UseAutonomyEventsOptions {
  taskId?: string;
  eventType?: string;
}

interface UseAutonomyEventsReturn {
  events: AutonomyEvent[];
  isConnected: boolean;
  connectionState: ConnectionState;
  error: Error | null;
  clearEvents: () => void;
}

export function useAutonomyEvents(options: UseAutonomyEventsOptions = {}): UseAutonomyEventsReturn {
  const { taskId, eventType } = options;
  const [events, setEvents] = useState<AutonomyEvent[]>([]);
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected');
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const params = new URLSearchParams();
    if (taskId) params.append('task', taskId);

    const client = createWsClient({
      url: `${wsUrl('/events')}?${params.toString()}`,
      silent: true, // Don't spam console
      maxRetries: 2,
      retryDelay: 5000,
      onConnect: () => {
        setConnectionState('connected');
        setError(null);
      },
      onDisconnect: () => {
        setConnectionState('disconnected');
      },
      onMessage: (data) => {
        try {
          const eventData = data as AutonomyEvent;
          
          // Filter by event type if specified
          const evType = eventData.type;
          if (eventType && evType !== eventType) {
            return;
          }
          
          setEvents(prev => [...prev, eventData]);
        } catch (err) {
          console.debug('Failed to parse autonomy event:', err);
        }
      },
    });

    // Delay connection to avoid spam on page load
    const connectTimeout = setTimeout(() => {
      client.connect();
    }, 1000);

    // Mark as unavailable if not connected after 10 seconds
    const unavailableTimeout = setTimeout(() => {
      if (client.getState() !== 'connected') {
        setConnectionState('unavailable');
        setError(new Error('WebSocket server not available - real-time updates disabled'));
      }
    }, 10000);

    return () => {
      clearTimeout(connectTimeout);
      clearTimeout(unavailableTimeout);
      client.disconnect();
    };
  }, [taskId, eventType]);

  const clearEvents = useCallback(() => {
    setEvents([]);
  }, []);

  return {
    events,
    isConnected: connectionState === 'connected',
    connectionState,
    error,
    clearEvents,
  };
}

interface UseAutonomyStateReturn {
  state: AutonomyState | null;
  isConnected: boolean;
  connectionState: ConnectionState;
}

export function useAutonomyState(taskId: string): UseAutonomyStateReturn {
  const [state, setState] = useState<AutonomyState | null>(null);
  const { events, isConnected, connectionState } = useAutonomyEvents({ taskId });

  useEffect(() => {
    const stateEvents = events.filter((e): e is AutonomyStateChangedEvent => e.type === 'autonomy.state_changed');
    if (stateEvents.length > 0) {
      const latest = stateEvents[stateEvents.length - 1];
      setState(latest.payload.state);
    }
  }, [events]);

  return { state, isConnected, connectionState };
}

interface UseCourseCorrectionsReturn {
  corrections: CourseCorrection[];
  isConnected: boolean;
  connectionState: ConnectionState;
}

export function useCourseCorrections(taskId: string): UseCourseCorrectionsReturn {
  const [corrections, setCorrections] = useState<CourseCorrection[]>([]);
  const { events, isConnected, connectionState } = useAutonomyEvents({ taskId, eventType: 'autonomy.course_correction' });

  useEffect(() => {
    const courseCorrections = events
      .filter((e): e is AutonomyCourseCorrectionEvent => e.type === 'autonomy.course_correction')
      .map(e => ({
        timestamp: e.timestamp,
        failed_step: e.payload.failed_step,
        recovery_steps: e.payload.recovery_steps,
      }));
    
    setCorrections(courseCorrections);
  }, [events]);

  return { corrections, isConnected, connectionState };
}

export default useAutonomyEvents;
