'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import useSWR from 'swr';
import { apiPath, apiJson } from '@/lib/api-client';
import type { LiveEventLatest } from '@/app/api/events/latest/route';

export type LiveEventStatus = 'connecting' | 'live' | 'reconnecting' | 'offline';

export interface LiveEvent {
  id: number;
  type: string;
  project_id?: string;
  task_id?: string;
  message?: string;
  rawAt: number;
}

const MAX_EVENTS = 50;
/** How long to wait for the socket to go 'live' before declaring 'offline' */
const OFFLINE_TIMEOUT_MS = 4000;
/** How often to retry the SSE connection when offline or reconnecting */
const RECONNECT_INTERVAL_MS = 10_000;

interface FallbackResponse {
  events: LiveEventLatest[];
}

export function useLiveEvents(projectId: string | null): {
  events: LiveEvent[];
  status: LiveEventStatus;
} {
  const [events, setEvents] = useState<LiveEvent[]>([]);
  const [status, setStatus] = useState<LiveEventStatus>('connecting');

  // Keep status in a ref so callbacks always read the latest value without stale closures
  const statusRef = useRef<LiveEventStatus>('connecting');
  // Counter for assigning local display IDs independent of server IDs
  const nextIdRef = useRef(0);
  // Refs for the EventSource and timers so cleanup is always deterministic
  const esRef = useRef<EventSource | null>(null);
  const offlineTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const updateStatus = useCallback((s: LiveEventStatus) => {
    statusRef.current = s;
    setStatus(s);
  }, []);

  const connect = useCallback(() => {
    // Guard: close any existing connection before opening a new one
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }

    // Transition: if we were live, mark as reconnecting; otherwise connecting
    updateStatus(statusRef.current === 'live' ? 'reconnecting' : 'connecting');

    // Start the offline fallback timer — if we don't reach 'live' in time, go offline
    if (offlineTimerRef.current) clearTimeout(offlineTimerRef.current);
    offlineTimerRef.current = setTimeout(() => {
      if (statusRef.current !== 'live') {
        updateStatus('offline');
      }
    }, OFFLINE_TIMEOUT_MS);

    const es = new EventSource(apiPath('/api/events'));
    esRef.current = es;

    es.onopen = () => {
      if (offlineTimerRef.current) {
        clearTimeout(offlineTimerRef.current);
        offlineTimerRef.current = null;
      }
      updateStatus('live');
    };

    es.addEventListener('message', (e) => {
      try {
        const parsed = JSON.parse(e.data);
        // Filter by project if specified
        if (projectId && parsed.project_id && parsed.project_id !== projectId) return;
        const entry: LiveEvent = {
          id: nextIdRef.current++,
          type: parsed.type ?? 'unknown',
          project_id: parsed.project_id,
          task_id: parsed.task_id,
          message: parsed.message ?? parsed.description,
          rawAt: typeof parsed.ts === 'number' ? parsed.ts : Date.now(),
        };
        setEvents((prev) => [...prev.slice(-(MAX_EVENTS - 1)), entry]);
      } catch {
        // ignore unparseable events
      }
    });

    es.onerror = () => {
      // Transition to reconnecting from 'live' or 'connecting' (engine_offline / immediate error)
      if (statusRef.current === 'live' || statusRef.current === 'connecting') {
        updateStatus('reconnecting');
        // Restart offline timer on error
        if (offlineTimerRef.current) clearTimeout(offlineTimerRef.current);
        offlineTimerRef.current = setTimeout(() => {
          if (statusRef.current !== 'live') {
            updateStatus('offline');
          }
        }, OFFLINE_TIMEOUT_MS);
      }
    };
  }, [projectId, updateStatus]);

  useEffect(() => {
    connect();

    // Periodic reconnect attempt — keeps trying every 10s when offline/reconnecting,
    // so the UI recovers automatically without a page reload
    reconnectTimerRef.current = setInterval(() => {
      if (statusRef.current === 'offline' || statusRef.current === 'reconnecting') {
        connect();
      }
    }, RECONNECT_INTERVAL_MS);

    return () => {
      esRef.current?.close();
      esRef.current = null;
      if (offlineTimerRef.current) {
        clearTimeout(offlineTimerRef.current);
        offlineTimerRef.current = null;
      }
      if (reconnectTimerRef.current) {
        clearInterval(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
    };
  }, [connect]);

  // Fallback polling: only active while offline — surfaces ring buffer snapshot via REST
  const { data: fallbackData } = useSWR<FallbackResponse>(
    status === 'offline' ? `/api/events/latest?limit=50` : null,
    (url: string) => apiJson<FallbackResponse>(url),
    { refreshInterval: 3000, dedupingInterval: 1500 }
  );

  // When fallback data arrives and we're still offline, surface it as a snapshot
  useEffect(() => {
    if (status !== 'offline' || !fallbackData?.events?.length) return;
    const fallbackEvents: LiveEvent[] = fallbackData.events
      .filter((e) => !projectId || !e.project_id || e.project_id === projectId)
      .map((e) => ({
        id: nextIdRef.current++,
        type: e.type,
        project_id: e.project_id,
        task_id: e.task_id,
        message: e.message,
        rawAt: e.ts,
      }));
    setEvents(fallbackEvents.slice(-MAX_EVENTS));
  }, [fallbackData, status, projectId]);

  return { events, status };
}
