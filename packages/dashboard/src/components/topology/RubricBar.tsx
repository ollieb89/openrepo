'use client';

import React from 'react';
import type { RubricScore } from '@/lib/types/topology';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

interface DimensionDef {
  key: keyof Omit<RubricScore, 'key_differentiators'>;
  label: string;
}

const DIMENSIONS: DimensionDef[] = [
  { key: 'complexity',             label: 'Cmplx' },
  { key: 'coordination_overhead', label: 'Coord' },
  { key: 'risk_containment',      label: 'Risk'  },
  { key: 'time_to_first_output',  label: 'Speed' },
  { key: 'cost_estimate',         label: 'Cost'  },
  { key: 'preference_fit',        label: 'Pref'  },
  { key: 'overall_confidence',    label: 'Conf'  },
];

function scoreColor(score: number): string {
  if (score >= 7) return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400';
  if (score >= 4) return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400';
  return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400';
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface RubricBarProps {
  score: RubricScore | undefined;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function RubricBar({ score }: RubricBarProps) {
  return (
    <div className="flex flex-wrap gap-1 py-1.5">
      {DIMENSIONS.map(({ key, label }) => {
        const value = score ? (score[key] as number) : null;
        const colorClass = value !== null ? scoreColor(value) : 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-500';

        return (
          <div
            key={key}
            className={`flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-medium ${colorClass}`}
            title={key.replace(/_/g, ' ')}
          >
            <span className="opacity-70">{label}</span>
            <span className="font-bold">{value !== null ? value.toFixed(1) : 'N/A'}</span>
          </div>
        );
      })}
    </div>
  );
}

export default RubricBar;
