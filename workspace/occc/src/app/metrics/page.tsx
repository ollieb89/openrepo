'use client';

import { useProject } from '@/context/ProjectContext';
import { useMetrics } from '@/lib/hooks/useMetrics';
import AgentTree from '@/components/agents/AgentTree';
import CompletionBarChart from '@/components/metrics/CompletionBarChart';
import PoolGauge from '@/components/metrics/PoolGauge';
import LifecycleStatCards from '@/components/metrics/LifecycleStatCards';
import MetricsSkeleton from '@/components/metrics/MetricsSkeleton';
import MetricsErrorCard from '@/components/metrics/MetricsErrorCard';

export default function MetricsPage() {
  const { projectId } = useProject();
  const { metrics, isLoading, error, refresh } = useMetrics(projectId);

  return (
    <div className="flex flex-col lg:flex-row gap-6 h-full">
      {/* Left column: Agent Hierarchy (~30%) */}
      <div className="w-full lg:w-[30%] shrink-0">
        <div className="mb-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Agent Hierarchy</h2>
          <p className="text-xs text-gray-500 dark:text-gray-400">Current agent structure</p>
        </div>
        <AgentTree key={projectId ?? 'none'} />
      </div>

      {/* Right column: Metrics (~70%) */}
      <div className="w-full lg:w-[70%] min-w-0">
        <div className="mb-4">
          <h1 className="text-xl font-bold text-gray-900 dark:text-white">Metrics</h1>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Task completion times, pool utilization, and container lifecycle stats
          </p>
        </div>

        {isLoading ? (
          <MetricsSkeleton />
        ) : error ? (
          <MetricsErrorCard onRetry={() => refresh()} />
        ) : metrics ? (
          <div className="space-y-6">
            {/* Lifecycle stat cards */}
            <LifecycleStatCards lifecycle={metrics.lifecycle} />

            {/* Bar chart */}
            <div>
              <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Task Completion Times
              </h3>
              <CompletionBarChart data={metrics.completionDurations} />
            </div>

            {/* Pool gauge */}
            <div>
              <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Pool Utilization
              </h3>
              <div className="flex justify-center">
                <div className="w-48">
                  <PoolGauge
                    pct={metrics.poolUtilization}
                    active={metrics.poolActive}
                    max={metrics.poolMax}
                  />
                </div>
              </div>
            </div>
          </div>
        ) : (
          <MetricsSkeleton />
        )}
      </div>
    </div>
  );
}
