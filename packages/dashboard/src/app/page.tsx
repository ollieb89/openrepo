'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import InferenceBadge from '@/components/common/InferenceBadge';
import Card from '@/components/common/Card';
import ContextCard from '@/components/common/ContextCard';
import { useProject } from '@/context/ProjectContext';
import { setProjectConsent } from '@/lib/privacy/consent-store';
import { runRuntimeInference, type RuntimeInferenceResult } from '@/lib/privacy/runtime-inference';
import { usePrivacy } from '@/lib/hooks/usePrivacy';
import { useEffect } from 'react';
import { Decision } from '@/lib/types/decisions';
import { apiPath } from '@/lib/api-client';

export default function Home() {
  const { projectId, project } = useProject();
  const { settings } = usePrivacy(projectId);
  const [prompt, setPrompt] = useState('Summarize progress and blockers for this feature area.');
  const [localConfidence, setLocalConfidence] = useState(0.4);
  const [result, setResult] = useState<RuntimeInferenceResult | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [recentDecisions, setRecentDecisions] = useState<Decision[]>([]);

  useEffect(() => {
    async function loadRecentDecisions() {
      try {
        const url = projectId ? apiPath(`/api/decisions?projectId=${projectId}`) : apiPath('/api/decisions');
        const res = await fetch(url);
        const data = await res.json();
        setRecentDecisions(data.slice(0, 3));
      } catch (err) {
        console.error('Failed to load recent decisions:', err);
      }
    }
    loadRecentDecisions();
  }, [projectId]);

  const hasConsent = settings?.remoteInferenceEnabled === true;
  const localConfidenceThreshold = Number(
    process.env.NEXT_PUBLIC_PRIVACY_LOCAL_CONFIDENCE_THRESHOLD ?? 0.6
  );

  const confidenceLabel = useMemo(() => {
    return `${Math.round(localConfidence * 100)}%`;
  }, [localConfidence]);

  async function runInference() {
    if (!projectId) return;

    setIsRunning(true);

    try {
      await setProjectConsent(projectId, hasConsent);
      const inferenceResult = await runRuntimeInference({
        projectId,
        prompt,
        localConfidence,
      });
      setResult(inferenceResult);
    } finally {
      setIsRunning(false);
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-2 space-y-6">
        <div className="flex items-end justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold text-gray-900 dark:text-white">Inference Preview</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Project: {project?.name ?? 'No project selected'}
            </p>
          </div>
          <Link
            href="/settings/privacy"
            className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Open Privacy Center
          </Link>
        </div>

        <Card className="p-5" title="Run Local/Remote Decision" subtitle="Low confidence can use remote only with explicit consent">
          <div className="space-y-4">
            <label className="block text-sm text-gray-700 dark:text-gray-300">
              Prompt
              <textarea
                className="mt-1 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900"
                rows={3}
                value={prompt}
                onChange={event => setPrompt(event.target.value)}
              />
            </label>

            <div>
              <div className="flex items-center justify-between text-sm text-gray-700 dark:text-gray-300">
                <span>Local confidence</span>
                <span>{confidenceLabel}</span>
              </div>
              <input
                type="range"
                min={0}
                max={1}
                step={0.01}
                value={localConfidence}
                onChange={event => setLocalConfidence(Number(event.target.value))}
                className="mt-2 w-full"
              />
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                Threshold: {Math.round(localConfidenceThreshold * 100)}%
              </p>
            </div>

            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={runInference}
                disabled={!projectId || isRunning}
                className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isRunning ? 'Running...' : 'Run inference'}
              </button>
              {!hasConsent && (
                <p className="text-xs text-amber-700 dark:text-amber-200">
                  Remote inference is disabled for this project.
                </p>
              )}
            </div>
          </div>
        </Card>

        {result && (
          <Card className="p-5" title="Result" subtitle="Provenance and deny-path messaging">
            <div className="space-y-3">
              <InferenceBadge mode={result.mode} reason={result.reason} />
              <p className="text-sm text-gray-800 dark:text-gray-100">{result.output}</p>
              {result.improvementNote && (
                <p className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:border-amber-700 dark:bg-amber-900/30 dark:text-amber-100">
                  {result.improvementNote}
                </p>
              )}
            </div>
          </Card>
        )}
      </div>

      <div className="space-y-6">
        <div>
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-bold text-gray-900 dark:text-white uppercase tracking-wider">Recent Decisions</h3>
            <Link href="/decisions" className="text-xs text-blue-600 hover:underline">View All</Link>
          </div>
          <div className="space-y-3">
            {recentDecisions.length > 0 ? (
              recentDecisions.map(decision => (
                <ContextCard key={decision.id} decision={decision} />
              ))
            ) : (
              <div className="bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-800 rounded-lg p-4 text-center">
                <p className="text-xs text-slate-500">No decisions extracted yet.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
