'use client';

import { useState, useEffect } from 'react';
import { ShieldAlert, X, WifiOff } from 'lucide-react';
import Link from 'next/link';
import type { EscalationEvent } from '@/lib/types/autonomy';
import { createWsClient, type ConnectionState } from '@/lib/ws-client';
import { wsUrl } from '@/lib/api-client';

export function EscalationAlertBanner() {
  const [escalations, setEscalations] = useState<EscalationEvent[]>([]);
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected');
  const [showConnectionStatus, setShowConnectionStatus] = useState(false);

  useEffect(() => {
    const wsEndpoint = wsUrl('/events');
    
    // Skip WebSocket if not configured
    if (!wsEndpoint || wsEndpoint === 'ws://' || wsEndpoint === 'wss://') {
      setConnectionState('unavailable');
      return;
    }
    
    const client = createWsClient({
      url: wsEndpoint,
      silent: true, // Don't spam console with connection errors
      maxRetries: 2, // Limited retries - server is optional
      retryDelay: 3000,
      onConnect: () => {
        setConnectionState('connected');
        setShowConnectionStatus(false);
      },
      onDisconnect: () => {
        setConnectionState('disconnected');
      },
      onMessage: (data) => {
        try {
          const eventData = data as Record<string, unknown>;
          const eventType = (eventData.event_type ?? eventData.type) as string;
          
          if (eventType === 'autonomy.escalation_triggered') {
            const escalation: EscalationEvent = {
              task_id: eventData.task_id as string,
              reason: (eventData.payload as Record<string, unknown>)?.reason as string,
              confidence: (eventData.payload as Record<string, unknown>)?.confidence as number,
              timestamp: Number(eventData.timestamp) || Date.now(),
            };
            
            setEscalations(prev => {
              if (prev.some(e => e.task_id === escalation.task_id)) {
                return prev;
              }
              return [...prev, escalation];
            });
            
            // Request desktop notification permission
            if (typeof window !== 'undefined' && 'Notification' in window) {
              if (Notification.permission === 'granted') {
                new Notification('Task Escalated', {
                  body: `${escalation.task_id}: ${escalation.reason}`,
                  icon: '/favicon.ico',
                });
              } else if (Notification.permission !== 'denied') {
                Notification.requestPermission().then(permission => {
                  if (permission === 'granted') {
                    new Notification('Task Escalated', {
                      body: `${escalation.task_id}: ${escalation.reason}`,
                      icon: '/favicon.ico',
                    });
                  }
                });
              }
            }
          }
        } catch (err) {
          console.debug('Failed to parse escalation event:', err);
        }
      },
    });

    // Delay initial connection attempt to avoid spam on page load
    const connectTimeout = setTimeout(() => {
      client.connect();
    }, 1000);

    // Show connection status if still disconnected after 5 seconds
    const statusTimeout = setTimeout(() => {
      if (client.getState() !== 'connected') {
        setConnectionState('unavailable');
        setShowConnectionStatus(true);
      }
    }, 5000);

    return () => {
      clearTimeout(connectTimeout);
      clearTimeout(statusTimeout);
      client.disconnect();
    };
  }, []);

  const dismiss = (taskId: string) => {
    setDismissed(prev => new Set(prev).add(taskId));
  };

  const activeEscalations = escalations.filter(e => !dismissed.has(e.task_id));

  // Don't render anything if no escalations and connection is fine or hidden
  if (activeEscalations.length === 0 && !showConnectionStatus) return null;

  return (
    <div className="fixed top-4 right-4 z-50 space-y-2 max-w-md">
      {/* Connection Status Warning - only shown when server is unavailable */}
      {showConnectionStatus && connectionState === 'unavailable' && (
        <div 
          className="bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-3 shadow-lg flex items-center gap-2"
        >
          <WifiOff className="h-4 w-4 text-gray-400" />
          <span className="text-xs text-gray-500 dark:text-gray-400">
            Real-time updates unavailable
          </span>
          <button 
            onClick={() => setShowConnectionStatus(false)}
            className="ml-auto text-gray-400 hover:text-gray-600"
          >
            <X className="h-3 w-3" />
          </button>
        </div>
      )}

      {/* Escalation Alerts */}
      {activeEscalations.map(esc => (
        <div 
          key={esc.task_id} 
          className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 shadow-lg animate-in fade-in slide-in-from-right"
        >
          <div className="flex items-start gap-3">
            <ShieldAlert className="h-5 w-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2">
                <h4 className="text-sm font-semibold text-red-900 dark:text-red-100">
                  Task Escalated
                </h4>
                <button 
                  onClick={() => dismiss(esc.task_id)}
                  className="text-red-400 hover:text-red-600 dark:hover:text-red-300"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <p className="text-sm text-red-800 dark:text-red-200 mt-1 font-medium truncate">
                {esc.task_id}
              </p>
              <p className="text-sm text-red-700 dark:text-red-300 mt-1">
                {esc.reason}
              </p>
              <p className="text-xs text-red-600 dark:text-red-400 mt-1">
                Confidence: {Math.round((esc.confidence || 0) * 100)}%
              </p>
              <div className="flex gap-2 mt-3">
                <Link 
                  href={`/tasks?id=${esc.task_id}`}
                  className="inline-flex items-center px-2.5 py-1.5 rounded text-xs font-medium bg-red-600 text-white hover:bg-red-700 transition-colors"
                >
                  View Task
                </Link>
                <button 
                  onClick={() => dismiss(esc.task_id)}
                  className="inline-flex items-center px-2.5 py-1.5 rounded text-xs font-medium border border-red-300 dark:border-red-700 text-red-700 dark:text-red-300 hover:bg-red-100 dark:hover:bg-red-800/30 transition-colors"
                >
                  Dismiss
                </button>
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export default EscalationAlertBanner;
