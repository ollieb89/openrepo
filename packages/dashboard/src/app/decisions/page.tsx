'use client';

import { useEffect, useState } from 'react';
import { useProject } from '@/context/ProjectContext';
import { DecisionCard } from '@/components/decisions/DecisionCard';
import { Decision } from '@/lib/types/decisions';

export default function DecisionsPage() {
  const { projectId, project } = useProject();
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchDecisions = async () => {
    if (!projectId) {
      setLoading(false);
      return;
    }
    try {
      const res = await fetch(`/api/decisions?projectId=${projectId}`);
      if (res.ok) {
        const data = await res.json();
        setDecisions(data);
      }
    } catch (error) {
      console.error('Failed to fetch decisions:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDecisions();
  }, [projectId]);

  const handleHide = async (id: string) => {
    try {
      const res = await fetch(`/api/decisions/${id}`, { method: 'DELETE' });
      if (res.ok) {
        setDecisions(prev => prev.filter(d => d.id !== id));
      }
    } catch (error) {
      console.error('Failed to hide decision:', error);
    }
  };

  const handleReSummarize = async (id: string, hint?: string) => {
    try {
      const res = await fetch(`/api/decisions/${id}/re-summarize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ hint }),
      });
      if (res.ok) {
        const updatedDecision = await res.json();
        setDecisions(prev => prev.map(d => d.id === id ? updatedDecision : d));
      }
    } catch (error) {
      console.error('Failed to re-summarize:', error);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-slate-500 animate-pulse">Loading decisions...</div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <header className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">Decision Log</h1>
        <p className="text-slate-600 dark:text-slate-400">
          Chronological record of project resolutions extracted from source communications.
        </p>
      </header>

      {!projectId ? (
        <div className="bg-slate-50 dark:bg-slate-900/50 rounded-lg border-2 border-dashed border-slate-200 dark:border-slate-800 p-12 text-center text-slate-500">
          Please select a project to view decisions.
        </div>
      ) : decisions.length === 0 ? (
        <div className="bg-slate-50 dark:bg-slate-900/50 rounded-lg border-2 border-dashed border-slate-200 dark:border-slate-800 p-12 text-center text-slate-500">
          No decisions found for <span className="font-semibold">{project?.name || projectId}</span> yet.
        </div>
      ) : (
        <div className="space-y-4">
          {decisions.map(decision => (
            <DecisionCard 
              key={decision.id} 
              decision={decision} 
              projectName={project?.name}
              onHide={handleHide}
              onReSummarize={handleReSummarize}
            />
          ))}
        </div>
      )}
    </div>
  );
}
