'use client';

// PipelineStage type — mirrors the shape from /api/pipeline/route.ts
export interface PipelineStage {
  name: string;
  status: 'pending' | 'active' | 'completed' | 'failed';
  timestamp?: number;
  duration?: number;
  agent?: string;
}

/**
 * Pure function — returns the Tailwind class string for a pipeline segment
 * based on its status. Exported for direct testing without rendering.
 */
export function getPipelineStripSegmentClass(status: PipelineStage['status']): string {
  switch (status) {
    case 'completed':
      return 'bg-green-500 dark:bg-green-600';
    case 'active':
      return 'bg-blue-500 dark:bg-blue-600 animate-pulse';
    case 'failed':
      return 'bg-red-500 dark:bg-red-600';
    case 'pending':
    default:
      return 'bg-gray-200 dark:bg-gray-700 border border-dashed border-gray-400 dark:border-gray-500';
  }
}

interface PipelineStripProps {
  stages: PipelineStage[];
  compact?: boolean;
}

/**
 * PipelineStrip renders 6 equal-width segments in a flex row.
 * - Each segment gets a status-based color class.
 * - Duration labels appear below only when stage.duration is defined.
 * - compact=true uses h-3; compact=false uses h-4.
 * - Shows a small warning icon if any non-pending stage has undefined timestamp.
 */
export function PipelineStrip({ stages, compact = false }: PipelineStripProps) {
  const heightClass = compact ? 'h-3' : 'h-4';

  // Check for incomplete timing: non-pending stage missing a timestamp
  const hasIncompleteTimestamp = stages.some(
    s => s.status !== 'pending' && s.timestamp === undefined
  );

  return (
    <div className="w-full">
      {/* Segment row */}
      <div className="flex gap-0.5 w-full">
        {stages.map((stage, index) => {
          const segClass = getPipelineStripSegmentClass(stage.status);
          const tooltipText = stage.duration !== undefined
            ? `${stage.name}: ${stage.status} (${stage.duration}s)`
            : `${stage.name}: ${stage.status}`;

          return (
            <div
              key={index}
              className={`flex-1 rounded-sm ${heightClass} ${segClass}`}
              title={tooltipText}
            />
          );
        })}

        {/* Warning icon for incomplete timing */}
        {hasIncompleteTimestamp && (
          <span
            className="ml-1 text-amber-500 text-xs leading-none self-center flex-shrink-0"
            title="incomplete timing"
            aria-label="incomplete timing"
          >
            !
          </span>
        )}
      </div>

      {/* Duration label row — only render row when at least one stage has duration */}
      {stages.some(s => s.duration !== undefined) && (
        <div className="flex gap-0.5 w-full mt-0.5">
          {stages.map((stage, index) => (
            <div key={index} className="flex-1 text-center">
              {stage.duration !== undefined && (
                <span className="text-xs text-gray-400 dark:text-gray-500 tabular-nums leading-none">
                  {stage.duration}s
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default PipelineStrip;
