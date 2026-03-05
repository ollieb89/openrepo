'use client';

import { useState } from 'react';
import { usePipeline } from '@/lib/hooks/usePipeline';
import { PipelineStrip } from '@/components/metrics/PipelineStrip';
import StatusBadge from '@/components/common/StatusBadge';
import type { TaskStatus } from '@/lib/types';

// PipelineItem mirrors /api/pipeline response shape
interface PipelineItem {
  taskId: string;
  projectId: string;
  stages: Array<{
    name: string;
    status: 'pending' | 'active' | 'completed' | 'failed';
    timestamp?: number;
    duration?: number;
    agent?: string;
  }>;
  totalDuration?: number;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
}

type StatusFilter = 'all' | 'pending' | 'in_progress' | 'completed' | 'failed';
type StageFilter = 'all' | 'L1' | 'L2' | 'L3';
type DurationFilter = 'all' | 'lt30' | '30to5m' | 'gt5m';

interface PipelineSectionProps {
  projectId: string | null;
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return secs > 0 ? `${mins}m ${secs}s` : `${mins}m`;
}

function matchesStageFilter(item: PipelineItem, stageFilter: StageFilter): boolean {
  if (stageFilter === 'all') return true;
  const activeStage = item.stages.find(s => s.status === 'active' || s.status === 'failed');
  if (!activeStage) return false;
  return activeStage.name.startsWith(stageFilter);
}

function matchesDurationFilter(item: PipelineItem, durationFilter: DurationFilter): boolean {
  if (durationFilter === 'all') return true;
  const d = item.totalDuration;
  if (d === undefined) return false;
  switch (durationFilter) {
    case 'lt30':
      return d < 30;
    case '30to5m':
      return d >= 30 && d <= 300;
    case 'gt5m':
      return d > 300;
    default:
      return true;
  }
}

function PipelineRowSkeleton() {
  return (
    <div className="animate-pulse space-y-2">
      {[1, 2, 3].map(i => (
        <div key={i} className="flex items-center gap-3 py-2">
          <div className="w-24 h-4 bg-gray-200 dark:bg-gray-700 rounded" />
          <div className="w-16 h-5 bg-gray-200 dark:bg-gray-700 rounded-full" />
          <div className="flex-1 h-3 bg-gray-200 dark:bg-gray-700 rounded" />
          <div className="w-12 h-4 bg-gray-200 dark:bg-gray-700 rounded" />
        </div>
      ))}
    </div>
  );
}

export function PipelineSection({ projectId }: PipelineSectionProps) {
  const { pipelines, isLoading } = usePipeline(projectId);

  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [stageFilter, setStageFilter] = useState<StageFilter>('all');
  const [durationFilter, setDurationFilter] = useState<DurationFilter>('all');

  // Client-side filtering
  const filtered = (pipelines as PipelineItem[]).filter(item => {
    if (statusFilter !== 'all' && item.status !== statusFilter) return false;
    if (!matchesStageFilter(item, stageFilter)) return false;
    if (!matchesDurationFilter(item, durationFilter)) return false;
    return true;
  });

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 dark:border-gray-700">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
          Pipeline Timeline
        </h3>
        <span className="text-xs text-gray-400 dark:text-gray-500">
          {filtered.length} task{filtered.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2 px-5 py-3 border-b border-gray-100 dark:border-gray-700">
        {/* Status filter */}
        <select
          value={statusFilter}
          onChange={e => setStatusFilter(e.target.value as StatusFilter)}
          className="text-xs rounded-md border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 px-2 py-1"
          aria-label="Filter by status"
        >
          <option value="all">All statuses</option>
          <option value="pending">Pending</option>
          <option value="in_progress">In progress</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
        </select>

        {/* Stage filter */}
        <select
          value={stageFilter}
          onChange={e => setStageFilter(e.target.value as StageFilter)}
          className="text-xs rounded-md border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 px-2 py-1"
          aria-label="Filter by stage"
        >
          <option value="all">All stages</option>
          <option value="L1">L1</option>
          <option value="L2">L2</option>
          <option value="L3">L3</option>
        </select>

        {/* Duration bucket filter */}
        <select
          value={durationFilter}
          onChange={e => setDurationFilter(e.target.value as DurationFilter)}
          className="text-xs rounded-md border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 px-2 py-1"
          aria-label="Filter by duration"
        >
          <option value="all">Any duration</option>
          <option value="lt30">&lt; 30s</option>
          <option value="30to5m">30s – 5m</option>
          <option value="gt5m">&gt; 5m</option>
        </select>
      </div>

      {/* Content */}
      <div className="px-5 py-3">
        {isLoading ? (
          <PipelineRowSkeleton />
        ) : filtered.length === 0 ? (
          <p className="text-sm text-gray-400 dark:text-gray-500 text-center py-6">
            No pipeline data available
          </p>
        ) : (
          <div className="space-y-3">
            {filtered.slice(0, 20).map(item => (
              <div
                key={item.taskId}
                className="flex items-center gap-3 py-1"
              >
                {/* Task ID */}
                <span className="font-mono text-xs text-gray-500 dark:text-gray-400 w-28 truncate flex-shrink-0">
                  {item.taskId}
                </span>

                {/* Status badge */}
                <div className="flex-shrink-0">
                  <StatusBadge status={item.status as TaskStatus} />
                </div>

                {/* Pipeline strip */}
                <div className="flex-1 min-w-0">
                  <PipelineStrip stages={item.stages} compact={true} />
                </div>

                {/* Total duration */}
                <span className="text-xs text-gray-400 dark:text-gray-500 flex-shrink-0 w-14 text-right tabular-nums">
                  {item.totalDuration !== undefined
                    ? formatDuration(item.totalDuration)
                    : '—'}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default PipelineSection;
