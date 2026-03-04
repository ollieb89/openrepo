'use client';

import React, { useState, useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import type { ChangelogEntry, RubricScore } from '@/lib/types/topology';

// ---------------------------------------------------------------------------
// Chart data type
// ---------------------------------------------------------------------------

export interface ChartDataPoint {
  event: number;
  lean?: number;
  balanced?: number;
  robust?: number;
  preference_fit?: number;
}

// ---------------------------------------------------------------------------
// Pure transformation function (exported for unit testing)
// ---------------------------------------------------------------------------

/**
 * Transform a changelog into chart-ready data points.
 * Only entries that have annotations.rubric_scores produce a data point.
 * preference_fit is taken from the average across archetypes (or the first available value).
 */
export function transformChangelogToChartData(changelog: ChangelogEntry[]): ChartDataPoint[] {
  const result: ChartDataPoint[] = [];

  for (let i = 0; i < changelog.length; i++) {
    const entry = changelog[i];
    const rubricScores = entry.annotations?.rubric_scores;
    if (!rubricScores) continue;

    const point: ChartDataPoint = { event: i + 1 };

    const lean = rubricScores['lean'];
    const balanced = rubricScores['balanced'];
    const robust = rubricScores['robust'];

    if (lean) point.lean = lean.overall_confidence;
    if (balanced) point.balanced = balanced.overall_confidence;
    if (robust) point.robust = robust.overall_confidence;

    // preference_fit: use first available archetype's preference_fit score
    const anyScore: RubricScore | undefined = lean ?? balanced ?? robust;
    if (anyScore) point.preference_fit = anyScore.preference_fit;

    result.push(point);
  }

  return result;
}

// ---------------------------------------------------------------------------
// Per-dimension expansion types
// ---------------------------------------------------------------------------

type Archetype = 'lean' | 'balanced' | 'robust';

const DIMENSIONS: Array<keyof Omit<RubricScore, 'key_differentiators'>> = [
  'complexity',
  'coordination_overhead',
  'risk_containment',
  'time_to_first_output',
  'cost_estimate',
  'preference_fit',
  'overall_confidence',
];

const DIMENSION_COLORS: Record<string, string> = {
  complexity:            '#ef4444',
  coordination_overhead: '#f97316',
  risk_containment:      '#84cc16',
  time_to_first_output:  '#06b6d4',
  cost_estimate:         '#8b5cf6',
  preference_fit:        '#f59e0b',
  overall_confidence:    '#3b82f6',
};

const DIMENSION_LABELS: Record<string, string> = {
  complexity:            'Complexity',
  coordination_overhead: 'Coord. Overhead',
  risk_containment:      'Risk Containment',
  time_to_first_output:  'Time to Output',
  cost_estimate:         'Cost Estimate',
  preference_fit:        'Preference Fit',
  overall_confidence:    'Confidence',
};

// ---------------------------------------------------------------------------
// Archetype colors
// ---------------------------------------------------------------------------

const ARCHETYPE_COLORS = {
  lean:     '#3b82f6',
  balanced: '#10b981',
  robust:   '#8b5cf6',
};

// ---------------------------------------------------------------------------
// Dimension chart data builder
// ---------------------------------------------------------------------------

function buildDimensionData(
  changelog: ChangelogEntry[],
  archetype: Archetype,
): Array<Record<string, number>> {
  const result: Array<Record<string, number>> = [];

  for (let i = 0; i < changelog.length; i++) {
    const rubricScores = changelog[i].annotations?.rubric_scores;
    if (!rubricScores) continue;
    const score = rubricScores[archetype];
    if (!score) continue;

    const point: Record<string, number> = { event: i + 1 };
    for (const dim of DIMENSIONS) {
      const val = score[dim];
      if (typeof val === 'number') point[dim] = val;
    }
    result.push(point);
  }

  return result;
}

// ---------------------------------------------------------------------------
// ConfidenceChart component
// ---------------------------------------------------------------------------

interface ConfidenceChartProps {
  changelog: ChangelogEntry[];
}

export function ConfidenceChart({ changelog }: ConfidenceChartProps) {
  const [expanded, setExpanded] = useState(false);
  const [selectedArchetype, setSelectedArchetype] = useState<Archetype>('balanced');

  const chartData = useMemo(() => transformChangelogToChartData(changelog), [changelog]);
  const dimensionData = useMemo(
    () => (expanded ? buildDimensionData(changelog, selectedArchetype) : []),
    [changelog, expanded, selectedArchetype],
  );

  const showReferenceLine = chartData.length >= 5;

  if (expanded) {
    return (
      <div className="flex flex-col gap-2">
        {/* Expanded header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setExpanded(false)}
              className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
            >
              Back to overview
            </button>
            <span className="text-gray-300 dark:text-gray-600">|</span>
            <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
              Per-dimension view:
            </span>
            <div className="flex gap-1">
              {(['lean', 'balanced', 'robust'] as Archetype[]).map((a) => (
                <button
                  key={a}
                  type="button"
                  onClick={() => setSelectedArchetype(a)}
                  className={[
                    'px-2 py-0.5 rounded text-[11px] font-medium capitalize transition-colors',
                    selectedArchetype === a
                      ? 'bg-gray-900 text-white dark:bg-gray-100 dark:text-gray-900'
                      : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700',
                  ].join(' ')}
                >
                  {a}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Dimension chart */}
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={dimensionData} margin={{ top: 4, right: 8, left: -20, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" className="opacity-20" />
            <XAxis dataKey="event" label={{ value: 'Correction', position: 'insideBottomRight', offset: -4, fontSize: 10 }} tick={{ fontSize: 10 }} />
            <YAxis domain={[0, 10]} tick={{ fontSize: 10 }} />
            <Tooltip contentStyle={{ fontSize: '11px' }} />
            <Legend iconSize={8} wrapperStyle={{ fontSize: '10px' }} />
            {DIMENSIONS.map((dim) => (
              <Line
                key={dim}
                type="monotone"
                dataKey={dim}
                name={DIMENSION_LABELS[dim]}
                stroke={DIMENSION_COLORS[dim]}
                strokeWidth={1.5}
                dot={{ r: 2 }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      {/* Overview header */}
      <div className="flex items-center justify-end">
        <button
          type="button"
          onClick={() => setExpanded(true)}
          className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
        >
          Per-dimension view
        </button>
      </div>

      {/* Overview chart */}
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={chartData} margin={{ top: 4, right: 8, left: -20, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" className="opacity-20" />
          <XAxis dataKey="event" label={{ value: 'Correction', position: 'insideBottomRight', offset: -4, fontSize: 10 }} tick={{ fontSize: 10 }} />
          <YAxis domain={[0, 10]} tick={{ fontSize: 10 }} />
          <Tooltip contentStyle={{ fontSize: '11px' }} />
          <Legend iconSize={8} wrapperStyle={{ fontSize: '10px' }} />

          {/* Archetype lines */}
          <Line
            type="monotone"
            dataKey="lean"
            name="Lean"
            stroke={ARCHETYPE_COLORS.lean}
            strokeWidth={2}
            dot={{ r: 3 }}
          />
          <Line
            type="monotone"
            dataKey="balanced"
            name="Balanced"
            stroke={ARCHETYPE_COLORS.balanced}
            strokeWidth={2}
            dot={{ r: 3 }}
          />
          <Line
            type="monotone"
            dataKey="robust"
            name="Robust"
            stroke={ARCHETYPE_COLORS.robust}
            strokeWidth={2}
            dot={{ r: 3 }}
          />

          {/* preference_fit — dashed amber */}
          <Line
            type="monotone"
            dataKey="preference_fit"
            name="Preference Fit"
            stroke="#f59e0b"
            strokeWidth={1}
            strokeDasharray="5 3"
            dot={false}
          />

          {/* Reference line at correction 5 */}
          {showReferenceLine && (
            <ReferenceLine
              x={5}
              stroke="#f59e0b"
              strokeDasharray="4 3"
              label={{ value: 'Pattern extraction begins', position: 'insideTopLeft', fontSize: 9, fill: '#f59e0b' }}
            />
          )}
        </LineChart>
      </ResponsiveContainer>

      {chartData.length === 0 && (
        <p className="text-xs text-gray-400 dark:text-gray-600 text-center -mt-2">
          No rubric score data available yet
        </p>
      )}
    </div>
  );
}

export default ConfidenceChart;
