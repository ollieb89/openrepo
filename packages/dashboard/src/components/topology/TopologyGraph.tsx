'use client';

import '@xyflow/react/dist/style.css';

import React, { useMemo, useCallback } from 'react';
import { ReactFlow, Background, Controls, useNodesState, useEdgesState } from '@xyflow/react';
import type { NodeMouseHandler } from '@xyflow/react';
import { toFlowElements } from './topology-utils';
import type { DiffHighlightMap } from './topology-utils';
import { TopologyNodeComponent } from './TopologyNode';
import type { TopologyNodeType } from './TopologyNode';
import { TopologyEdgeComponent } from './TopologyEdge';
import type { TopologyEdgeType } from './TopologyEdge';
import type { TopologyGraph as TopologyGraphData } from '@/lib/types/topology';

// ---------------------------------------------------------------------------
// nodeTypes / edgeTypes MUST be defined OUTSIDE the component for stable reference.
// Defining inside causes re-mount flickering on every render.
// ---------------------------------------------------------------------------

const nodeTypes = { topologyNode: TopologyNodeComponent } as const;
const edgeTypes = { topologyEdge: TopologyEdgeComponent } as const;

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface TopologyGraphProps {
  graph: TopologyGraphData | null;
  diffHighlights?: DiffHighlightMap;
  title?: string;
  className?: string;
  onNodeClick?: (nodeId: string) => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function TopologyGraph({
  graph,
  diffHighlights,
  title,
  className = '',
  onNodeClick,
}: TopologyGraphProps) {
  // Compute React Flow elements (memoized on graph + diffHighlights)
  const { nodes: initialNodes, edges: initialEdges } = useMemo(() => {
    if (!graph) return { nodes: [], edges: [] };
    return toFlowElements(graph, diffHighlights);
  }, [graph, diffHighlights]);

  const [nodes, , onNodesChange] = useNodesState<TopologyNodeType>(initialNodes as TopologyNodeType[]);
  const [edges, , onEdgesChange] = useEdgesState<TopologyEdgeType>(initialEdges as TopologyEdgeType[]);

  const handleNodeClick: NodeMouseHandler<TopologyNodeType> = useCallback(
    (_event, node) => {
      onNodeClick?.(node.id);
    },
    [onNodeClick],
  );

  // Empty state
  if (!graph) {
    return (
      <div className={`flex items-center justify-center h-[400px] bg-gray-50 dark:bg-gray-900 rounded-lg border border-dashed border-gray-300 dark:border-gray-700 ${className}`}>
        <div className="text-center text-gray-500 dark:text-gray-400">
          <div className="text-4xl mb-2">⬡</div>
          <p className="text-sm font-medium">No topology available</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`flex flex-col gap-1 ${className}`}>
      {title && (
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 px-1">{title}</h3>
      )}
      {/* ReactFlow parent MUST have explicit height */}
      <div className="relative h-[400px] rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden bg-white dark:bg-gray-900">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={handleNodeClick}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          proOptions={{ hideAttribution: true }}
        >
          <Background gap={16} />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
    </div>
  );
}

export default TopologyGraph;
