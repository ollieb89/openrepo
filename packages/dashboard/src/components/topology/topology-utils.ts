/**
 * topology-utils.ts
 * Data transformation utilities: TopologyGraph JSON to React Flow nodes/edges with dagre layout.
 */

import Dagre from '@dagrejs/dagre';
import type { Node, Edge } from '@xyflow/react';
import type { TopologyGraph, TopologyNode, TopologyEdge, TopologyDiff } from '@/lib/types/topology';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

export const NODE_WIDTH = 180;
export const NODE_HEIGHT = 60;

// Edge visual style mapping (locked decision from plan 02 context)
export const EDGE_STYLE: Record<
  TopologyEdge['edge_type'],
  { stroke: string; strokeDasharray?: string; strokeWidth: number }
> = {
  delegation:       { stroke: '#3b82f6', strokeWidth: 2 },
  coordination:     { stroke: '#10b981', strokeDasharray: '6 3', strokeWidth: 1.5 },
  escalation:       { stroke: '#f59e0b', strokeDasharray: '2 2', strokeWidth: 1.5 },
  review_gate:      { stroke: '#8b5cf6', strokeWidth: 3 },
  information_flow: { stroke: '#6b7280', strokeDasharray: '4 4', strokeWidth: 1 },
};

// ---------------------------------------------------------------------------
// Diff highlight map
// ---------------------------------------------------------------------------

export type DiffHighlightMap = {
  nodes: Record<string, 'added' | 'removed' | 'modified'>;
  edges: Record<string, 'added' | 'removed'>;
};

/**
 * Build a highlight map from a TopologyDiff object.
 * Edge keys use the format "from_role->to_role".
 */
export function computeDiffHighlights(diff: TopologyDiff): DiffHighlightMap {
  const nodes: DiffHighlightMap['nodes'] = {};
  const edges: DiffHighlightMap['edges'] = {};

  for (const n of diff.added_nodes) {
    nodes[n.id] = 'added';
  }
  for (const n of diff.removed_nodes) {
    nodes[n.id] = 'removed';
  }
  for (const n of diff.modified_nodes) {
    nodes[n.id] = 'modified';
  }
  for (const e of diff.added_edges) {
    edges[`${e.from_role}->${e.to_role}`] = 'added';
  }
  for (const e of diff.removed_edges) {
    edges[`${e.from_role}->${e.to_role}`] = 'removed';
  }

  return { nodes, edges };
}

// ---------------------------------------------------------------------------
// Node/Edge data types for React Flow
// ---------------------------------------------------------------------------

export interface TopologyNodeData extends Record<string, unknown> {
  id: string;
  level: 1 | 2 | 3;
  intent: string;
  risk_level: 'low' | 'medium' | 'high';
  highlight?: 'added' | 'removed' | 'modified';
}

export interface TopologyEdgeData extends Record<string, unknown> {
  edge_type: TopologyEdge['edge_type'];
  highlight?: 'added' | 'removed';
}

// ---------------------------------------------------------------------------
// toFlowElements
// ---------------------------------------------------------------------------

/**
 * Convert a TopologyGraph JSON to positioned React Flow nodes and styled edges.
 * Uses dagre (top-down layout) for automatic positioning.
 */
export function toFlowElements(
  graph: TopologyGraph,
  diffHighlights?: DiffHighlightMap,
): { nodes: Node<TopologyNodeData>[]; edges: Edge<TopologyEdgeData>[] } {
  if (!graph.nodes.length && !graph.edges.length) {
    return { nodes: [], edges: [] };
  }

  // Build dagre graph
  const g = new Dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: 'TB', nodesep: 60, ranksep: 80 });

  for (const node of graph.nodes) {
    g.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  }
  for (const edge of graph.edges) {
    g.setEdge(edge.from_role, edge.to_role);
  }

  Dagre.layout(g);

  // Convert nodes
  const nodes: Node<TopologyNodeData>[] = graph.nodes.map((n: TopologyNode) => {
    const dagreNode = g.node(n.id);
    return {
      id: n.id,
      type: 'topologyNode',
      position: {
        x: dagreNode ? dagreNode.x - NODE_WIDTH / 2 : 0,
        y: dagreNode ? dagreNode.y - NODE_HEIGHT / 2 : 0,
      },
      data: {
        id: n.id,
        level: n.level,
        intent: n.intent,
        risk_level: n.risk_level,
        highlight: diffHighlights?.nodes[n.id],
      },
    };
  });

  // Convert edges
  const edges: Edge<TopologyEdgeData>[] = graph.edges.map((e: TopologyEdge, idx: number) => {
    const edgeKey = `${e.from_role}->${e.to_role}`;
    const style = EDGE_STYLE[e.edge_type];
    return {
      id: `e-${e.from_role}-${e.to_role}-${idx}`,
      source: e.from_role,
      target: e.to_role,
      type: 'topologyEdge',
      style,
      data: {
        edge_type: e.edge_type,
        highlight: diffHighlights?.edges[edgeKey],
      },
    };
  });

  return { nodes, edges };
}
