'use client';

import { useState, useEffect, useCallback } from 'react';
import { useProject } from '@/context/ProjectContext';
import { MetricCard } from '@/components/metrics/MetricCard';
import { StatusDistributionChart, type StatusDistributionPoint } from '@/components/metrics/StatusDistributionChart';
import { TrendLineChart, type MetricsTrends } from '@/components/metrics/TrendLineChart';
import { AgentLeaderboard, type AgentMetrics } from '@/components/metrics/AgentLeaderboard';
import { TaskDataTable } from '@/components/metrics/TaskDataTable';
import { TimeRangeSelector, type TimeRange, type CustomRange } from '@/components/metrics/TimeRangeSelector';
import { PipelineSection } from '@/components/metrics/PipelineSection';
import { apiJson } from '@/lib/api-client';
import type { Task } from '@/lib/types';

// Types for API responses
interface MetricsSummary {
  completion_rate: number;
  completion_trend: 'up' | 'down' | 'neutral';
  completion_trend_value: string;
  throughput: number;
  throughput_trend: 'up' | 'down' | 'neutral';
  throughput_trend_value: string;
  cycle_time_ms: number;
  cycle_time_trend: 'up' | 'down' | 'neutral';
  cycle_time_trend_value: string;
  wip_count: number;
  wip_trend: 'up' | 'down' | 'neutral';
  wip_trend_value: string;
  failure_rate: number;
  failure_trend: 'up' | 'down' | 'neutral';
  failure_trend_value: string;
}

interface TasksResponse {
  tasks: Task[];
  projectId: string;
}

interface AgentsResponse {
  agents: AgentMetrics[];
}

interface TrendsResponse {
  trends: MetricsTrends;
}

interface SummaryResponse {
  summary: MetricsSummary;
}

interface StatusDistributionResponse {
  distribution: StatusDistributionPoint[];
}

function getDaysFromTimeRange(timeRange: TimeRange, customRange?: CustomRange): number | null {
  switch (timeRange) {
    case '7d':
      return 7;
    case '30d':
      return 30;
    case '90d':
      return 90;
    case 'all':
      return null; // No limit
    case 'custom':
      if (customRange) {
        const diffTime = customRange.end.getTime() - customRange.start.getTime();
        return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
      }
      return 30;
    default:
      return 30;
  }
}

export default function MetricsDashboard() {
  const { projectId } = useProject();
  
  // State
  const [timeRange, setTimeRange] = useState<TimeRange>('7d');
  const [customRange, setCustomRange] = useState<CustomRange | undefined>(undefined);
  const [summary, setSummary] = useState<MetricsSummary | null>(null);
  const [trends, setTrends] = useState<MetricsTrends | null>(null);
  const [agents, setAgents] = useState<AgentMetrics[] | null>(null);
  const [tasks, setTasks] = useState<Task[] | null>(null);
  const [statusDistribution, setStatusDistribution] = useState<StatusDistributionPoint[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Pagination state for task table
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  const fetchData = useCallback(async () => {
    if (!projectId) return;

    setLoading(true);
    setError(null);

    try {
      const days = getDaysFromTimeRange(timeRange, customRange);
      
      // Build query parameters
      const daysParam = days !== null ? `&days=${days}` : '';
      const projectParam = `project=${projectId}`;

      // Fetch all data in parallel
      const [
        summaryRes,
        trendsRes,
        agentsRes,
        tasksRes,
        distributionRes,
      ] = await Promise.all([
        // Summary
        apiJson<SummaryResponse>(`/api/metrics/summary?${projectParam}${daysParam}`).catch(() => null),
        // Trends
        apiJson<TrendsResponse>(`/api/metrics/trends?${projectParam}${daysParam}&granularity=daily`).catch(() => null),
        // Agents
        apiJson<AgentsResponse>(`/api/metrics/agents?${projectParam}${daysParam}`).catch(() => null),
        // Tasks (get all for filtering, paginate client-side)
        apiJson<TasksResponse>(`/api/tasks?${projectParam}`).catch(() => null),
        // Status distribution
        apiJson<StatusDistributionResponse>(`/api/metrics/distribution?${projectParam}${daysParam}`).catch(() => null),
      ]);

      setSummary(summaryRes?.summary || null);
      setTrends(trendsRes?.trends || null);
      setAgents(agentsRes?.agents || null);
      setTasks(tasksRes?.tasks || null);
      setStatusDistribution(distributionRes?.distribution || null);
    } catch (err) {
      console.error('Error fetching metrics data:', err);
      setError('Failed to load metrics data');
    } finally {
      setLoading(false);
    }
  }, [projectId, timeRange, customRange]);

  // Fetch data when time range or project changes
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Reset to page 1 when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [timeRange, customRange]);

  const handleTimeRangeChange = (range: TimeRange, custom?: CustomRange) => {
    setTimeRange(range);
    setCustomRange(custom);
  };

  if (!projectId) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
            No Project Selected
          </h2>
          <p className="text-gray-500 dark:text-gray-400">
            Please select a project to view metrics
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Task Metrics
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Monitor task completion, throughput, and agent performance
          </p>
        </div>
      </div>

      {/* Time Range Selector */}
      <div className="flex items-center">
        <TimeRangeSelector
          value={timeRange}
          customRange={customRange}
          onChange={handleTimeRangeChange}
        />
      </div>

      {/* Error State */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <div className="flex items-center gap-3">
            <svg className="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="text-sm text-red-700 dark:text-red-400">{error}</p>
            <button
              onClick={fetchData}
              className="ml-auto text-sm text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300 font-medium"
            >
              Retry
            </button>
          </div>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <MetricCard
          title="Completion Rate"
          value={summary?.completion_rate ?? 0}
          format="percent"
          trend={summary?.completion_trend}
          trendValue={summary?.completion_trend_value}
          loading={loading}
        />
        <MetricCard
          title="Throughput"
          value={summary?.throughput ?? 0}
          format="number"
          trend={summary?.throughput_trend}
          trendValue={summary?.throughput_trend_value}
          loading={loading}
        />
        <MetricCard
          title="Cycle Time"
          value={summary?.cycle_time_ms ?? 0}
          format="duration"
          trend={summary?.cycle_time_trend}
          trendValue={summary?.cycle_time_trend_value}
          loading={loading}
        />
        <MetricCard
          title="WIP"
          value={summary?.wip_count ?? 0}
          format="number"
          trend={summary?.wip_trend}
          trendValue={summary?.wip_trend_value}
          loading={loading}
        />
        <MetricCard
          title="Failure Rate"
          value={summary?.failure_rate ?? 0}
          format="percent"
          trend={summary?.failure_trend}
          trendValue={summary?.failure_trend_value}
          loading={loading}
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <TrendLineChart 
          data={trends} 
          loading={loading} 
        />
        <StatusDistributionChart 
          data={statusDistribution || []} 
          loading={loading} 
        />
      </div>

      {/* Agent Leaderboard */}
      <AgentLeaderboard 
        agents={agents || []} 
        loading={loading} 
      />

      {/* Task Data Table */}
      <TaskDataTable
        tasks={tasks}
        loading={loading}
        currentPage={currentPage}
        pageSize={pageSize}
        onPageChange={setCurrentPage}
      />

      {/* Pipeline Timeline */}
      <PipelineSection projectId={projectId} />
    </div>
  );
}
