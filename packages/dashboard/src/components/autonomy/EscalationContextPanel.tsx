'use client';

import { ShieldAlert, Play, XCircle, WifiOff } from 'lucide-react';
import Card from '@/components/common/Card';
import AutonomyStateBadge from './AutonomyStateBadge';
import { useAutonomyEvents } from '@/hooks/useAutonomyEvents';
import { useProject } from '@/context/ProjectContext';
import type { AutonomyEvent, TaskWithAutonomy } from '@/lib/types/autonomy';
import { apiFetch } from '@/lib/api-client';

interface EscalationContextPanelProps {
  task: TaskWithAutonomy;
}

function formatTimestamp(timestamp: number): string {
  return new Date(timestamp * 1000).toLocaleString();
}

function formatTime(timestamp: number): string {
  return new Date(timestamp * 1000).toLocaleTimeString();
}

export function EscalationContextPanel({ task }: EscalationContextPanelProps) {
  const { projectId } = useProject();
  const { events, connectionState } = useAutonomyEvents({ taskId: task.id });

  if (!task.autonomy?.escalation) return null;

  const escalation = task.autonomy.escalation;
  const history = events.filter((e: AutonomyEvent) =>
    e.type.startsWith('autonomy.')
  );

  const handleResume = async () => {
    try {
      const url = `/api/tasks/${task.id}/resume${projectId ? `?project=${projectId}` : ''}`;
      await apiFetch(url, { method: 'POST' });
    } catch (err) {
      console.error('Failed to resume task:', err);
    }
  };

  const handleFail = async () => {
    try {
      const url = `/api/tasks/${task.id}/fail${projectId ? `?project=${projectId}` : ''}`;
      await apiFetch(url, { method: 'POST' });
    } catch (err) {
      console.error('Failed to fail task:', err);
    }
  };

  return (
    <Card className="border-red-200 dark:border-red-800 bg-red-50/50 dark:bg-red-900/10">
      <div className="p-4">
        <div className="flex items-center gap-2 mb-4">
          <ShieldAlert className="h-5 w-5 text-red-600 dark:text-red-400" />
          <h4 className="text-sm font-semibold text-red-900 dark:text-red-100">
            Escalation Details
          </h4>
        </div>

        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <p className="text-xs text-gray-500 dark:text-gray-400">Reason</p>
            <p className="text-sm font-medium text-gray-900 dark:text-white">
              {escalation.reason}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500 dark:text-gray-400">Confidence at Escalation</p>
            <p className="text-sm font-medium text-red-600 dark:text-red-400">
              {Math.round(escalation.confidence * 100)}%
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500 dark:text-gray-400">Escalated At</p>
            <p className="text-sm font-medium text-gray-900 dark:text-white">
              {formatTimestamp(escalation.timestamp)}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500 dark:text-gray-400">Status</p>
            <AutonomyStateBadge state={task.autonomy.state} />
          </div>
        </div>

        <hr className="border-red-200 dark:border-red-800 my-4" />

        <div>
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
            Autonomy Event History
          </p>
          <div className="max-h-48 overflow-y-auto space-y-1">
            {history.length === 0 ? (
              <p className="text-sm text-gray-400 italic">No events recorded</p>
            ) : (
              history.map((event, i) => (
                <div key={i} className="flex gap-2 text-sm">
                  <span className="text-gray-400 text-xs">
                    {formatTime(event.timestamp)}
                  </span>
                  <span className="inline-flex items-center px-1.5 rounded text-xs bg-gray-100 dark:bg-gray-700">
                    {event.type.replace('autonomy.', '')}
                  </span>
                  {'score' in event.payload && (
                    <span className="text-gray-600 dark:text-gray-400">
                      confidence: {Math.round((event.payload as { score: number }).score * 100)}%
                    </span>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

        {task.autonomy.state === 'escalating' && (
          <div className="flex gap-2 mt-4">
            <button
              onClick={handleResume}
              className="inline-flex items-center gap-1 px-3 py-1.5 rounded text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 transition-colors"
            >
              <Play className="h-3.5 w-3.5" />
              Resume Task
            </button>
            <button
              onClick={handleFail}
              className="inline-flex items-center gap-1 px-3 py-1.5 rounded text-sm font-medium bg-red-600 text-white hover:bg-red-700 transition-colors"
            >
              <XCircle className="h-3.5 w-3.5" />
              Mark Failed
            </button>
          </div>
        )}
      </div>
    </Card>
  );
}

export default EscalationContextPanel;
