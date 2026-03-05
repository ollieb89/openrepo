'use client';

import Link from 'next/link';
import { useProject } from '@/context/ProjectContext';
import { useAgents } from '@/lib/hooks/useAgents';
import { useMetrics } from '@/lib/hooks/useMetrics';

export default function SwarmStatusPanel() {
  const { projectId } = useProject();
  const { agents } = useAgents(projectId);
  const { metrics } = useMetrics(projectId);

  const l1 = agents.filter(a => a.level === 1);
  const l2 = agents.filter(a => a.level === 2);
  const l3Active = metrics?.poolActive ?? 0;
  const poolMax = metrics?.poolMax ?? 3;
  const poolBars = Array.from({ length: poolMax }, (_, i) => i < l3Active);

  const total = (metrics?.lifecycle.completed ?? 0) + (metrics?.lifecycle.failed ?? 0);
  const successRate = total > 0
    ? Math.round(((metrics?.lifecycle.completed ?? 0) / total) * 100)
    : null;

  // todayCostUsd and todayTokens are not yet tracked in MetricsResponse;
  // keep the conditional render guarded for when they are added.
  const todayCostUsdVal = null as number | null;
  const todayTokensVal = null as number | null;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 flex flex-col gap-3">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
        Swarm Status
      </h3>

      {/* Agent hierarchy */}
      <div className="space-y-1 text-sm">
        {l1.map(a => (
          <div key={a.id} className="flex items-center gap-2">
            <span
              role="img"
              aria-label="L1 agent active"
              className="w-2 h-2 rounded-full bg-green-500 flex-shrink-0"
            />
            <span className="font-mono text-gray-700 dark:text-gray-300 text-xs">{a.name}</span>
            <span className="text-xs text-gray-400">L1</span>
          </div>
        ))}
        {l2.map(a => (
          <div key={a.id} className="flex items-center gap-2 ml-4">
            <span
              role="img"
              aria-label="L2 agent active"
              className="w-2 h-2 rounded-full bg-blue-500 flex-shrink-0"
            />
            <span className="font-mono text-gray-700 dark:text-gray-300 text-xs">{a.name}</span>
            <span className="text-xs text-gray-400">L2</span>
          </div>
        ))}
        <div className="flex items-center gap-2 ml-8">
          <span
            role="img"
            aria-label={l3Active > 0 ? 'L3 agents active' : 'L3 agents idle'}
            className={`w-2 h-2 rounded-full flex-shrink-0 ${l3Active > 0 ? 'bg-amber-500' : 'bg-gray-300'}`}
          />
          <span className="font-mono text-gray-700 dark:text-gray-300 text-xs">L3 Specialists</span>
          <span className="text-xs text-gray-400">{l3Active}/{poolMax} active</span>
        </div>
      </div>

      {/* Pool gauge */}
      <div>
        <div className="flex gap-1 mt-1">
          {poolBars.map((active, i) => (
            <div
              key={i}
              className={`h-2 flex-1 rounded-sm ${active ? 'bg-amber-400' : 'bg-gray-200 dark:bg-gray-700'}`}
            />
          ))}
        </div>
        <p className="text-xs text-gray-400 mt-1">Pool: {l3Active}/{poolMax}</p>
      </div>

      {/* Success rate */}
      <div className="flex items-center justify-between text-xs">
        <span className="text-gray-500 dark:text-gray-400">Success rate</span>
        <span className="font-semibold text-gray-800 dark:text-gray-100">{successRate ?? '—'}%</span>
      </div>

      {/* Cost (placeholder until token tracking is implemented) */}
      {todayCostUsdVal != null && todayTokensVal != null && (
        <div className="flex items-center justify-between text-xs border-t border-gray-100 dark:border-gray-700 pt-2">
          <span className="text-gray-500 dark:text-gray-400">Today</span>
          <span className="font-mono text-gray-700 dark:text-gray-300">
            ~${todayCostUsdVal.toFixed(2)} · {(todayTokensVal / 1_000_000).toFixed(1)}M tok
          </span>
        </div>
      )}

      <Link href="/agents" className="text-xs text-blue-600 hover:underline mt-auto">
        View agents →
      </Link>
    </div>
  );
}
