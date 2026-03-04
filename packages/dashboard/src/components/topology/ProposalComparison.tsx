'use client';

import React, { useMemo } from 'react';
import { TopologyGraph } from './TopologyGraph';
import { RubricBar } from './RubricBar';
import type { ProposalSet, TopologyProposal } from '@/lib/types/topology';

// ---------------------------------------------------------------------------
// Archetype visual config
// ---------------------------------------------------------------------------

const ARCHETYPE_CONFIG: Record<
  TopologyProposal['archetype'],
  { label: string; badgeClass: string }
> = {
  lean: {
    label: 'Lean',
    badgeClass: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300',
  },
  balanced: {
    label: 'Balanced',
    badgeClass: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
  },
  robust: {
    label: 'Robust',
    badgeClass: 'bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-300',
  },
};

const ARCHETYPES: TopologyProposal['archetype'][] = ['lean', 'balanced', 'robust'];

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface ProposalComparisonProps {
  proposals: ProposalSet | null;
  onNodeClick?: (nodeId: string) => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ProposalComparison({ proposals, onNodeClick }: ProposalComparisonProps) {
  // Find the archetype with highest overall_confidence
  const highestConfidenceArchetype = useMemo(() => {
    if (!proposals?.proposals.length) return null;
    return proposals.proposals.reduce((best, p) => {
      const bestConf = best?.rubric_score?.overall_confidence ?? -Infinity;
      const pConf = p.rubric_score?.overall_confidence ?? -Infinity;
      return pConf > bestConf ? p : best;
    }, proposals.proposals[0]).archetype;
  }, [proposals]);

  // Empty state
  if (!proposals || !proposals.proposals.length) {
    return (
      <div className="flex items-center justify-center h-[300px] bg-gray-50 dark:bg-gray-900 rounded-lg border border-dashed border-gray-300 dark:border-gray-700">
        <div className="text-center text-gray-500 dark:text-gray-400">
          <div className="text-3xl mb-2">⬡</div>
          <p className="text-sm font-medium">No proposals available</p>
          <p className="text-xs mt-1 opacity-70">Run a topology proposal to see options here</p>
        </div>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      {ARCHETYPES.map((arch) => {
        const proposal = proposals.proposals.find((p) => p.archetype === arch);
        const config = ARCHETYPE_CONFIG[arch];
        const isTopPick = arch === highestConfidenceArchetype;

        return (
          <div
            key={arch}
            className={[
              'flex flex-col gap-2 p-3 rounded-lg border bg-white dark:bg-gray-900',
              isTopPick
                ? 'border-blue-400 dark:border-blue-500 ring-1 ring-blue-400 dark:ring-blue-500 shadow-md'
                : 'border-gray-200 dark:border-gray-700',
            ].join(' ')}
          >
            {/* Archetype header */}
            <div className="flex items-center justify-between">
              <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${config.badgeClass}`}>
                {config.label}
              </span>
              {isTopPick && (
                <span className="text-[10px] font-semibold text-blue-600 dark:text-blue-400 uppercase tracking-wide">
                  Top Pick
                </span>
              )}
            </div>

            {/* Smaller graph — h-[250px] */}
            <div className="relative">
              <TopologyGraph
                graph={proposal?.topology ?? null}
                className="[&_.h-\[400px\]]:h-[250px]"
                onNodeClick={onNodeClick}
              />
            </div>

            {/* Rubric scores */}
            {proposal && (
              <RubricBar score={proposal.rubric_score} />
            )}

            {/* Key differentiators */}
            {proposal?.rubric_score?.key_differentiators?.length ? (
              <div>
                <p className="text-[10px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1">
                  Key Differentiators
                </p>
                <ul className="space-y-0.5">
                  {proposal.rubric_score.key_differentiators.slice(0, 3).map((diff, i) => (
                    <li key={i} className="text-xs text-gray-700 dark:text-gray-300 flex gap-1.5">
                      <span className="text-gray-400 mt-0.5 flex-shrink-0">•</span>
                      <span>{diff}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            {/* Justification snippet */}
            {proposal?.justification && (
              <div>
                <p className="text-[10px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1">
                  Justification
                </p>
                <p className="text-xs text-gray-600 dark:text-gray-400 line-clamp-3">
                  {proposal.justification}
                </p>
              </div>
            )}

            {/* Fallback if no proposal for this archetype */}
            {!proposal && (
              <p className="text-xs text-gray-400 dark:text-gray-600 italic text-center py-4">
                No {config.label} proposal available
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
}

export default ProposalComparison;
