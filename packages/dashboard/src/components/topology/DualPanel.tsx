'use client';

import React, { useState, useMemo } from 'react';
import { TopologyGraph } from './TopologyGraph';
import { RubricBar } from './RubricBar';
import { computeDiffHighlights } from './topology-utils';
import type { DiffHighlightMap } from './topology-utils';
import type {
  ProposalSet,
  TopologyGraph as TopologyGraphData,
  TopologyDiff,
  TopologyProposal,
} from '@/lib/types/topology';

// ---------------------------------------------------------------------------
// Archetype tab config
// ---------------------------------------------------------------------------

const ARCHETYPES: TopologyProposal['archetype'][] = ['lean', 'balanced', 'robust'];

const ARCHETYPE_LABELS: Record<TopologyProposal['archetype'], string> = {
  lean:     'Lean',
  balanced: 'Balanced',
  robust:   'Robust',
};

const ARCHETYPE_BADGE: Record<TopologyProposal['archetype'], string> = {
  lean:     'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  balanced: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  robust:   'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
};

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface DualPanelProps {
  proposals: ProposalSet | null;
  approved: TopologyGraphData | null;
  diff?: TopologyDiff;
  onNodeClick?: (nodeId: string) => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function DualPanel({ proposals, approved, diff, onNodeClick }: DualPanelProps) {
  const [activeArchetype, setActiveArchetype] = useState<TopologyProposal['archetype']>('lean');

  // Compute diff highlight map once
  const diffHighlights: DiffHighlightMap | undefined = useMemo(
    () => (diff ? computeDiffHighlights(diff) : undefined),
    [diff],
  );

  // Find the active proposal
  const activeProposal = useMemo(
    () => proposals?.proposals.find((p) => p.archetype === activeArchetype) ?? null,
    [proposals, activeArchetype],
  );

  const confidenceStr = (proposal: typeof activeProposal): string => {
    const conf = proposal?.rubric_score?.overall_confidence;
    return conf !== undefined ? `${conf.toFixed(1)}` : '–';
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* ------------------------------------------------------------------ */}
      {/* LEFT PANEL: Proposed topology with archetype tabs                   */}
      {/* ------------------------------------------------------------------ */}
      <div className="flex flex-col gap-2">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Proposed</h3>
          {activeProposal && (
            <span className="text-xs text-gray-500 dark:text-gray-400">
              Confidence: <span className="font-semibold text-gray-900 dark:text-gray-100">{confidenceStr(activeProposal)}</span>
            </span>
          )}
        </div>

        {/* Archetype tabs */}
        <div className="flex gap-1">
          {ARCHETYPES.map((arch) => {
            const proposal = proposals?.proposals.find((p) => p.archetype === arch);
            const conf = proposal?.rubric_score?.overall_confidence;
            const isActive = arch === activeArchetype;

            return (
              <button
                key={arch}
                onClick={() => setActiveArchetype(arch)}
                className={[
                  'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all',
                  isActive
                    ? 'bg-gray-900 text-white dark:bg-gray-100 dark:text-gray-900 shadow-sm'
                    : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700',
                ].join(' ')}
              >
                <span className={`px-1 py-0.5 rounded text-[10px] font-bold ${ARCHETYPE_BADGE[arch]}`}>
                  {ARCHETYPE_LABELS[arch]}
                </span>
                {conf !== undefined && (
                  <span className="opacity-75">{conf.toFixed(1)}</span>
                )}
              </button>
            );
          })}
        </div>

        {/* Proposed graph */}
        <TopologyGraph
          graph={activeProposal?.topology ?? null}
          diffHighlights={diffHighlights}
          onNodeClick={onNodeClick}
        />

        {/* RubricBar for active proposal */}
        {activeProposal && (
          <RubricBar score={activeProposal.rubric_score} />
        )}
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* RIGHT PANEL: Approved topology                                      */}
      {/* ------------------------------------------------------------------ */}
      <div className="flex flex-col gap-2">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Approved</h3>

        {approved ? (
          <TopologyGraph
            graph={approved}
            diffHighlights={diffHighlights}
            onNodeClick={onNodeClick}
          />
        ) : (
          <div className="flex items-center justify-center h-[400px] bg-gray-50 dark:bg-gray-900 rounded-lg border border-dashed border-gray-300 dark:border-gray-700">
            <div className="text-center text-gray-500 dark:text-gray-400 px-4">
              <div className="text-3xl mb-2">⬡</div>
              <p className="text-sm font-medium">No approved topology yet</p>
              <p className="text-xs mt-1 opacity-70">Approve a proposal to see it here</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default DualPanel;
