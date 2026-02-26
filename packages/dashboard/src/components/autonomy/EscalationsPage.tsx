'use client';

import { useState, useEffect } from 'react';
import { CheckCircle } from 'lucide-react';
import Link from 'next/link';
import Card from '@/components/common/Card';
import AutonomyStateBadge from './AutonomyStateBadge';
import { useProject } from '@/context/ProjectContext';
import type { TaskWithAutonomy, AutonomyState } from '@/lib/types/autonomy';

interface EscalationCardProps {
  task: TaskWithAutonomy;
  onResume: (taskId: string) => void;
}

function formatRelativeTime(timestamp: number): string {
  const seconds = Math.floor((Date.now() / 1000) - timestamp);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function EscalationCard({ task, onResume }: EscalationCardProps) {
  return (
    <Card className="border-red-200 dark:border-red-800">
      <div className="p-4">
        <div className="flex justify-between items-start mb-2">
          <div>
            <h3 className="text-base font-semibold text-gray-900 dark:text-white">
              {task.title || 'Untitled Task'}
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 font-mono">{task.id}</p>
          </div>
          <AutonomyStateBadge state={task.autonomy?.state as AutonomyState || 'escalating'} />
        </div>
        
        <p className="text-sm text-gray-700 dark:text-gray-300 mb-3">
          {task.autonomy?.escalation?.reason || 'No reason provided'}
        </p>
        
        <div className="flex justify-between items-center text-sm mb-3">
          <span className="text-gray-500 dark:text-gray-400">
            Confidence: {Math.round((task.autonomy?.escalation?.confidence || 0) * 100)}%
          </span>
          <span className="text-gray-400 dark:text-gray-500">
            {task.autonomy?.escalation?.timestamp 
              ? formatRelativeTime(task.autonomy.escalation.timestamp)
              : 'Unknown time'}
          </span>
        </div>
        
        <div className="flex gap-2">
          <Link 
            href={`/tasks?id=${task.id}`}
            className="inline-flex items-center px-3 py-1.5 rounded text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 transition-colors"
          >
            View Details
          </Link>
          {task.autonomy?.state === 'escalating' && (
            <button
              onClick={() => onResume(task.id)}
              className="inline-flex items-center px-3 py-1.5 rounded text-sm font-medium border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            >
              Resume
            </button>
          )}
        </div>
      </div>
    </Card>
  );
}

export function EscalationsPage() {
  const { projectId } = useProject();
  const [tasks, setTasks] = useState<TaskWithAutonomy[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!projectId) return;
    const fetchEscalatedTasks = async () => {
      try {
        const response = await fetch(`/api/tasks?state=escalating&project=${projectId}`);
        if (response.ok) {
          const { tasks: rawTasks } = await response.json();
          const tasksList = Array.isArray(rawTasks) ? rawTasks : [];
          // Sort by escalation timestamp (newest first)
          const sorted = tasksList.sort((a: TaskWithAutonomy, b: TaskWithAutonomy) =>
            (b.autonomy?.escalation?.timestamp || 0) - (a.autonomy?.escalation?.timestamp || 0)
          );
          setTasks(sorted);
        }
      } catch (err) {
        console.error('Failed to fetch escalated tasks:', err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchEscalatedTasks();
  }, [projectId]);

  const handleResume = async (taskId: string) => {
    try {
      const url = projectId ? `/api/tasks/${taskId}/resume?project=${projectId}` : `/api/tasks/${taskId}/resume`;
      await fetch(url, { method: 'POST' });
      setTasks(prev => prev.filter(t => t.id !== taskId));
    } catch (err) {
      console.error('Failed to resume task:', err);
    }
  };

  if (!projectId) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500 dark:text-gray-400">
        Select a project to view escalated tasks.
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500 dark:text-gray-400">
        Loading escalated tasks...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Escalated Tasks</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Tasks requiring operator intervention
          </p>
        </div>
        {tasks.length > 0 && (
          <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300">
            {tasks.length} requiring attention
          </span>
        )}
      </div>
      
      {tasks.length === 0 ? (
        <Card>
          <div className="py-12 text-center">
            <CheckCircle className="h-12 w-12 mx-auto mb-4 text-green-500" />
            <p className="text-gray-500 dark:text-gray-400">
              No escalated tasks. All autonomy agents running smoothly.
            </p>
          </div>
        </Card>
      ) : (
        <div className="grid gap-4">
          {tasks.map(task => (
            <EscalationCard key={task.id} task={task} onResume={handleResume} />
          ))}
        </div>
      )}
    </div>
  );
}

export default EscalationsPage;
