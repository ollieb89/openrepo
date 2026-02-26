'use client';

import { useState, useEffect } from 'react';
import { ShieldAlert, X } from 'lucide-react';
import Link from 'next/link';
import type { EscalationEvent } from '@/lib/types/autonomy';

export function EscalationAlertBanner() {
  const [escalations, setEscalations] = useState<EscalationEvent[]>([]);
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());

  useEffect(() => {
    // Connect to WebSocket for escalation events
    const ws = new WebSocket('ws://localhost:8080/events');
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        const eventType = data.event_type ?? data.type;
        if (eventType === 'autonomy.escalation_triggered') {
          const escalation: EscalationEvent = {
            task_id: data.task_id,
            reason: data.payload.reason,
            confidence: data.payload.confidence,
            timestamp: data.timestamp,
          };
          
          setEscalations(prev => {
            // Avoid duplicates
            if (prev.some(e => e.task_id === escalation.task_id)) {
              return prev;
            }
            return [...prev, escalation];
          });
          
          // Request desktop notification permission and show notification
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
        console.error('Failed to parse escalation event:', err);
      }
    };
    
    return () => ws.close();
  }, []);

  const dismiss = (taskId: string) => {
    setDismissed(prev => new Set(prev).add(taskId));
  };

  const activeEscalations = escalations.filter(e => !dismissed.has(e.task_id));

  if (activeEscalations.length === 0) return null;

  return (
    <div className="fixed top-4 right-4 z-50 space-y-2 max-w-md">
      {activeEscalations.map(esc => (
        <div 
          key={esc.task_id} 
          className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 shadow-lg"
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
                Confidence: {Math.round(esc.confidence * 100)}%
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
