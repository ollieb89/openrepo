import { describe, it, expect } from 'vitest';
import { toFlowElements, computeDiffHighlights } from '@/components/topology/topology-utils';
import type { TopologyGraph, TopologyDiff } from '@/lib/types/topology';

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const TWO_NODE_GRAPH: TopologyGraph = {
  project_id: 'test-project',
  version: 1,
  created_at: '2026-03-04T00:00:00Z',
  nodes: [
    { id: 'orchestrator', level: 1, intent: 'Coordinate all tasks', risk_level: 'low' },
    { id: 'worker',       level: 3, intent: 'Execute file writes', risk_level: 'medium' },
  ],
  edges: [
    { from_role: 'orchestrator', to_role: 'worker', edge_type: 'delegation' },
  ],
};

const EMPTY_GRAPH: TopologyGraph = {
  project_id: 'empty',
  version: 1,
  created_at: '2026-03-04T00:00:00Z',
  nodes: [],
  edges: [],
};

// ---------------------------------------------------------------------------
// TOBS-01, TOBS-02: Transform tests
// ---------------------------------------------------------------------------

describe('toFlowElements', () => {
  it('converts TopologyGraph nodes to React Flow nodes with dagre positions', () => {
    const { nodes } = toFlowElements(TWO_NODE_GRAPH);

    expect(nodes).toHaveLength(2);

    const orchestratorNode = nodes.find((n) => n.id === 'orchestrator');
    const workerNode = nodes.find((n) => n.id === 'worker');

    expect(orchestratorNode).toBeDefined();
    expect(workerNode).toBeDefined();

    // Positions should be numbers (dagre layout applied)
    expect(typeof orchestratorNode!.position.x).toBe('number');
    expect(typeof orchestratorNode!.position.y).toBe('number');
    expect(typeof workerNode!.position.x).toBe('number');
    expect(typeof workerNode!.position.y).toBe('number');

    // Data fields should be present
    expect(orchestratorNode!.data.level).toBe(1);
    expect(orchestratorNode!.data.intent).toBe('Coordinate all tasks');
    expect(orchestratorNode!.data.risk_level).toBe('low');

    // Node type
    expect(orchestratorNode!.type).toBe('topologyNode');
  });

  it('converts TopologyGraph edges to React Flow edges with correct source/target', () => {
    const { edges } = toFlowElements(TWO_NODE_GRAPH);

    expect(edges).toHaveLength(1);

    const edge = edges[0];
    expect(edge.source).toBe('orchestrator');
    expect(edge.target).toBe('worker');
    expect(edge.type).toBe('topologyEdge');
    expect(edge.data?.edge_type).toBe('delegation');
  });

  it('handles empty graph gracefully', () => {
    const { nodes, edges } = toFlowElements(EMPTY_GRAPH);

    expect(nodes).toHaveLength(0);
    expect(edges).toHaveLength(0);
  });

  it('applies diff highlights to nodes and edges', () => {
    const diff: TopologyDiff = {
      added_nodes: [{ id: 'worker', level: 3, intent: 'Execute file writes', risk_level: 'medium' }],
      removed_nodes: [],
      modified_nodes: [],
      added_edges: [],
      removed_edges: [],
      modified_edges: [],
      summary: 'Added worker node',
    };

    const highlights = computeDiffHighlights(diff);
    const { nodes } = toFlowElements(TWO_NODE_GRAPH, highlights);

    const workerNode = nodes.find((n) => n.id === 'worker');
    expect(workerNode?.data.highlight).toBe('added');

    const orchestratorNode = nodes.find((n) => n.id === 'orchestrator');
    expect(orchestratorNode?.data.highlight).toBeUndefined();
  });
});
