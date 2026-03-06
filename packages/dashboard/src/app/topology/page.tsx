'use client';

import '@xyflow/react/dist/style.css';

import React, { useState, useMemo } from 'react';
import { useTopology, useTopologyChangelog } from '@/lib/hooks/useTopology';
import { useProject } from '@/context/ProjectContext';
import { DualPanel } from '@/components/topology/DualPanel';
import { ProposalComparison } from '@/components/topology/ProposalComparison';
import { CorrectionTimeline } from '@/components/topology/CorrectionTimeline';
import { ConfidenceChart } from '@/components/topology/ConfidenceChart';
import { NodeDetailPanel } from '@/components/topology/NodeDetailPanel';
import type { TopologyDiff, ChangelogEntry } from '@/lib/types/topology';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

type ActiveView = 'dual' | 'comparison';

function formatTimestamp(ts: string): string {
  try {
    return new Date(ts).toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return ts;
  }
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function TopologyPage() {
  // Project ID from context — reactive to project switching
  const { projectId } = useProject();

  // Data hooks
  const { topology, isLoading: topoLoading, error: topoError } = useTopology(projectId);
  const { changelog, isLoading: changelogLoading, error: changelogError } = useTopologyChangelog(projectId);

  // UI state
  const [activeView, setActiveView] = useState<ActiveView>('dual');
  const [selectedEventIndex, setSelectedEventIndex] = useState<number | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  // Time-travel: get the diff from the selected changelog event
  const selectedEntry: ChangelogEntry | null = useMemo(() => {
    if (selectedEventIndex === null || !changelog.length) return null;
    return changelog[selectedEventIndex] ?? null;
  }, [selectedEventIndex, changelog]);

  const timeTravelDiff: TopologyDiff | undefined = selectedEntry?.diff ?? undefined;

  // Handlers
  const handleSelectEvent = (index: number) => {
    setSelectedEventIndex((prev) => (prev === index ? null : index));
  };

  const handleClearTimeTravel = () => setSelectedEventIndex(null);

  const handleNodeClick = (nodeId: string) => {
    setSelectedNodeId((prev) => (prev === nodeId ? null : nodeId));
  };

  // ---------------------------------------------------------------------------
  // Loading state
  // ---------------------------------------------------------------------------
  if (topoLoading || changelogLoading) {
    return (
      <div className="flex-1 p-6">
        <div className="flex items-center justify-center h-64 text-gray-500 dark:text-gray-400">
          <div className="flex flex-col items-center gap-3">
            <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            <p className="text-sm">Loading topology data...</p>
          </div>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Error state
  // ---------------------------------------------------------------------------
  if (topoError || changelogError) {
    return (
      <div className="flex-1 p-6">
        <div className="p-4 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-sm text-red-700 dark:text-red-400">
          Failed to load topology data. Check that the backend API is accessible and a project is selected.
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Empty state (no project selected or no data)
  // ---------------------------------------------------------------------------
  const hasData = topology?.proposals || topology?.approved;
  if (!projectId || !hasData) {
    return (
      <div className="flex-1 p-6">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-xl font-bold text-gray-900 dark:text-white">Topology</h1>
          {projectId && (
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">Project: {projectId}</p>
          )}
        </div>

        <div className="flex flex-col items-center justify-center h-64 text-gray-500 dark:text-gray-400 text-center">
          <div className="text-5xl mb-4 text-gray-300 dark:text-gray-700">⬡</div>
          <p className="text-base font-medium text-gray-700 dark:text-gray-300">
            No topology proposals yet
          </p>
          <p className="text-sm mt-2 max-w-sm opacity-70">
            Run{' '}
            <code className="px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 font-mono text-xs">
              openclaw propose
            </code>{' '}
            to generate topology proposals for this project.
          </p>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Main view
  // ---------------------------------------------------------------------------
  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div className="flex-1 overflow-y-auto p-6 space-y-6">

        {/* ---------------------------------------------------------------- */}
        {/* Header                                                            */}
        {/* ---------------------------------------------------------------- */}
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">Topology</h1>
            {projectId && (
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
                Project: <span className="font-medium">{projectId}</span>
              </p>
            )}
          </div>

          {/* View toggle */}
          <div className="flex items-center gap-1 bg-gray-100 dark:bg-gray-800 rounded-lg p-1">
            <button
              type="button"
              onClick={() => setActiveView('dual')}
              className={[
                'px-3 py-1.5 rounded-md text-sm font-medium transition-colors',
                activeView === 'dual'
                  ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200',
              ].join(' ')}
            >
              Dual Panel
            </button>
            <button
              type="button"
              onClick={() => setActiveView('comparison')}
              className={[
                'px-3 py-1.5 rounded-md text-sm font-medium transition-colors',
                activeView === 'comparison'
                  ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200',
              ].join(' ')}
            >
              Compare All
            </button>
          </div>
        </div>

        {/* ---------------------------------------------------------------- */}
        {/* Time-travel banner                                                */}
        {/* ---------------------------------------------------------------- */}
        {selectedEntry && selectedEventIndex !== null && (
          <div className="flex items-start gap-3 p-3 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700">
            <span className="flex-shrink-0 text-amber-500 mt-0.5">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </span>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-amber-800 dark:text-amber-300">
                Viewing correction #{selectedEventIndex + 1}
                {selectedEntry.diff?.summary && `: ${selectedEntry.diff.summary}`}
              </p>
              <p className="text-xs text-amber-600 dark:text-amber-400 mt-0.5">
                {formatTimestamp(selectedEntry.timestamp)} — diff highlights shown on current topology
              </p>
            </div>
            <button
              type="button"
              onClick={handleClearTimeTravel}
              className="flex-shrink-0 text-xs font-medium text-amber-700 dark:text-amber-400 hover:text-amber-900 dark:hover:text-amber-200 underline"
            >
              Back to current
            </button>
          </div>
        )}

        {/* ---------------------------------------------------------------- */}
        {/* Main topology area                                                */}
        {/* ---------------------------------------------------------------- */}
        {activeView === 'dual' ? (
          <DualPanel
            proposals={topology.proposals}
            approved={topology.approved}
            diff={timeTravelDiff}
            onNodeClick={handleNodeClick}
          />
        ) : (
          <ProposalComparison
            proposals={topology.proposals}
            onNodeClick={handleNodeClick}
          />
        )}

        {/* ---------------------------------------------------------------- */}
        {/* Below main area: CorrectionTimeline + ConfidenceChart             */}
        {/* ---------------------------------------------------------------- */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left: CorrectionTimeline */}
          <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
            <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">
              Correction History
              {changelog.length > 0 && (
                <span className="ml-2 text-xs font-normal text-gray-400">
                  ({changelog.length} correction{changelog.length !== 1 ? 's' : ''})
                </span>
              )}
            </h2>
            <CorrectionTimeline
              changelog={changelog}
              selectedIndex={selectedEventIndex}
              onSelectEvent={handleSelectEvent}
            />
          </div>

          {/* Right: ConfidenceChart */}
          <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
            <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">
              Confidence Evolution
            </h2>
            <ConfidenceChart changelog={changelog} />
          </div>
        </div>

      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Node Detail Panel (absolutely positioned)                           */}
      {/* ------------------------------------------------------------------ */}
      <NodeDetailPanel
        nodeId={selectedNodeId}
        proposals={topology.proposals}
        approved={topology.approved}
        onClose={() => setSelectedNodeId(null)}
      />
    </div>
  );
}
