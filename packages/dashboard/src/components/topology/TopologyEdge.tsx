'use client';

import React from 'react';
import { getBezierPath, EdgeLabelRenderer } from '@xyflow/react';
import type { EdgeProps, Edge } from '@xyflow/react';
import { EDGE_STYLE } from './topology-utils';
import type { TopologyEdge } from '@/lib/types/topology';

// ---------------------------------------------------------------------------
// Data type for the custom edge
// ---------------------------------------------------------------------------

export interface TopologyEdgeData extends Record<string, unknown> {
  edge_type: TopologyEdge['edge_type'];
  highlight?: 'added' | 'removed';
}

export type TopologyEdgeType = Edge<TopologyEdgeData, 'topologyEdge'>;

// ---------------------------------------------------------------------------
// Diff highlight stroke overrides
// ---------------------------------------------------------------------------

const HIGHLIGHT_STROKE: Record<string, string> = {
  added:   '#22c55e',  // green-500
  removed: '#ef4444',  // red-500
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function TopologyEdgeComponent({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
}: EdgeProps<TopologyEdgeType>) {
  const edgeType: TopologyEdge['edge_type'] = data?.edge_type ?? 'delegation';
  const highlight = data?.highlight;

  const baseStyle = EDGE_STYLE[edgeType] ?? EDGE_STYLE.delegation;

  // Override stroke color for diff highlights
  const stroke = highlight ? (HIGHLIGHT_STROKE[highlight] ?? baseStyle.stroke) : baseStyle.stroke;
  const opacity = highlight === 'removed' ? 0.6 : 1;

  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  return (
    <>
      <path
        id={id}
        d={edgePath}
        fill="none"
        stroke={stroke}
        strokeWidth={baseStyle.strokeWidth}
        strokeDasharray={baseStyle.strokeDasharray}
        opacity={opacity}
        className="react-flow__edge-path"
      />
      <EdgeLabelRenderer>
        <div
          style={{
            position: 'absolute',
            transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
            pointerEvents: 'none',
          }}
          className="nodrag nopan"
        >
          <span
            className="text-[9px] font-medium px-1 py-0.5 rounded"
            style={{
              color: stroke,
              backgroundColor: 'rgba(255,255,255,0.85)',
              border: `1px solid ${stroke}`,
              opacity: 0.9,
            }}
          >
            {edgeType.replace('_', ' ')}
          </span>
        </div>
      </EdgeLabelRenderer>
    </>
  );
}

export default TopologyEdgeComponent;
