'use client';

import React, { useEffect, useCallback } from 'react';
import type { ProposalSet, TopologyGraph, TopologyNode, TopologyEdge } from '@/lib/types/topology';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const RISK_BADGE: Record<TopologyNode['risk_level'], string> = {
  low:    'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300',
  medium: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
  high:   'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
};

const EDGE_TYPE_BADGE: Record<TopologyEdge['edge_type'], string> = {
  delegation:       'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
  coordination:     'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300',
  escalation:       'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
  review_gate:      'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300',
  information_flow: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300',
};

function edgeTypeLabel(type: TopologyEdge['edge_type']): string {
  return type.replace(/_/g, ' ');
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface NodeDetailPanelProps {
  nodeId: string | null;
  proposals: ProposalSet | null;
  approved: TopologyGraph | null;
  onClose: () => void;
}

// ---------------------------------------------------------------------------
// NodeDetailPanel
// ---------------------------------------------------------------------------

export function NodeDetailPanel({ nodeId, proposals, approved, onClose }: NodeDetailPanelProps) {
  // Close on Escape
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    },
    [onClose],
  );

  useEffect(() => {
    if (nodeId) {
      document.addEventListener('keydown', handleKeyDown);
    }
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [nodeId, handleKeyDown]);

  if (!nodeId) return null;

  // Find the node in approved topology first, then proposals
  let foundNode: TopologyNode | undefined;
  let foundEdges: TopologyEdge[] = [];

  if (approved) {
    foundNode = approved.nodes.find((n) => n.id === nodeId);
    if (foundNode) {
      foundEdges = approved.edges.filter(
        (e) => e.from_role === nodeId || e.to_role === nodeId,
      );
    }
  }

  // Determine which archetypes include this role
  const archetypePresence: Array<{ archetype: string; level: number | undefined }> = [];
  if (proposals?.proposals) {
    for (const proposal of proposals.proposals) {
      const n = proposal.topology.nodes.find((pn) => pn.id === nodeId);
      if (n) {
        archetypePresence.push({ archetype: proposal.archetype, level: n.level });
        // If not already found in approved, use the proposal node data
        if (!foundNode) {
          foundNode = n;
          foundEdges = proposal.topology.edges.filter(
            (e) => e.from_role === nodeId || e.to_role === nodeId,
          );
        }
      }
    }
  }

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/10 dark:bg-black/30"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Slide-in panel */}
      <aside
        role="dialog"
        aria-label={`Node details for ${nodeId}`}
        className="fixed right-0 top-0 z-50 h-full w-80 max-w-full bg-white dark:bg-gray-900 border-l border-gray-200 dark:border-gray-700 shadow-xl flex flex-col overflow-hidden"
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-2 p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex-1 min-w-0">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-gray-400 dark:text-gray-500 mb-0.5">
              Node Details
            </p>
            <h2 className="text-base font-bold text-gray-900 dark:text-white truncate">
              {nodeId}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex-shrink-0 mt-0.5 p-1.5 rounded-md text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            aria-label="Close panel"
          >
            <svg className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
              <path
                fillRule="evenodd"
                d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                clipRule="evenodd"
              />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-5">
          {foundNode ? (
            <>
              {/* Role info */}
              <section>
                <p className="text-[10px] font-semibold uppercase tracking-widest text-gray-400 dark:text-gray-500 mb-2">
                  Role Info
                </p>
                <dl className="grid grid-cols-2 gap-y-2 gap-x-3">
                  <dt className="text-xs text-gray-500 dark:text-gray-400">Level</dt>
                  <dd className="text-xs font-medium text-gray-900 dark:text-white">
                    L{foundNode.level}
                  </dd>

                  <dt className="text-xs text-gray-500 dark:text-gray-400">Risk</dt>
                  <dd>
                    <span
                      className={`px-1.5 py-0.5 rounded text-[11px] font-medium capitalize ${RISK_BADGE[foundNode.risk_level]}`}
                    >
                      {foundNode.risk_level}
                    </span>
                  </dd>

                  {foundNode.estimated_load !== undefined && (
                    <>
                      <dt className="text-xs text-gray-500 dark:text-gray-400">Est. Load</dt>
                      <dd className="text-xs font-medium text-gray-900 dark:text-white">
                        {foundNode.estimated_load}
                      </dd>
                    </>
                  )}
                </dl>
              </section>

              {/* Intent */}
              <section>
                <p className="text-[10px] font-semibold uppercase tracking-widest text-gray-400 dark:text-gray-500 mb-1">
                  Intent
                </p>
                <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
                  {foundNode.intent}
                </p>
              </section>

              {/* Edges */}
              {foundEdges.length > 0 && (
                <section>
                  <p className="text-[10px] font-semibold uppercase tracking-widest text-gray-400 dark:text-gray-500 mb-2">
                    Edges ({foundEdges.length})
                  </p>
                  <ul className="space-y-1.5">
                    {foundEdges.map((edge, i) => {
                      const direction = edge.from_role === nodeId ? 'out' : 'in';
                      const peer = direction === 'out' ? edge.to_role : edge.from_role;
                      return (
                        <li key={i} className="flex items-start gap-2">
                          <span
                            className="flex-shrink-0 mt-0.5 text-[10px] font-bold text-gray-400 dark:text-gray-500 uppercase"
                          >
                            {direction === 'out' ? '→' : '←'}
                          </span>
                          <div className="flex-1 min-w-0">
                            <span className="text-xs text-gray-700 dark:text-gray-300 font-medium truncate block">
                              {peer}
                            </span>
                            <span
                              className={`mt-0.5 inline-block px-1.5 py-0.5 rounded text-[10px] font-medium ${EDGE_TYPE_BADGE[edge.edge_type]}`}
                            >
                              {edgeTypeLabel(edge.edge_type)}
                            </span>
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                </section>
              )}

              {/* Archetype presence */}
              {archetypePresence.length > 0 && (
                <section>
                  <p className="text-[10px] font-semibold uppercase tracking-widest text-gray-400 dark:text-gray-500 mb-2">
                    Present in Archetypes
                  </p>
                  <ul className="space-y-1">
                    {archetypePresence.map(({ archetype, level }) => (
                      <li key={archetype} className="flex items-center gap-2 text-xs">
                        <span className="capitalize font-medium text-gray-700 dark:text-gray-300">
                          {archetype}
                        </span>
                        {level !== undefined && (
                          <span className="text-gray-400 dark:text-gray-500">— L{level}</span>
                        )}
                      </li>
                    ))}
                  </ul>
                </section>
              )}
            </>
          ) : (
            <div className="py-8 text-center text-gray-400 dark:text-gray-600">
              <p className="text-sm">Node &quot;{nodeId}&quot; not found in current topology.</p>
            </div>
          )}
        </div>
      </aside>
    </>
  );
}

export default NodeDetailPanel;
