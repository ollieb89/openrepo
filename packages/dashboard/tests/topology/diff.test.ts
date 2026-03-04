import { describe, it, expect } from 'vitest';
import { computeDiffHighlights } from '@/components/topology/topology-utils';
import type { TopologyDiff } from '@/lib/types/topology';

// ---------------------------------------------------------------------------
// Helper: build a minimal empty diff
// ---------------------------------------------------------------------------
function emptyDiff(overrides: Partial<TopologyDiff> = {}): TopologyDiff {
  return {
    added_nodes:    [],
    removed_nodes:  [],
    modified_nodes: [],
    added_edges:    [],
    removed_edges:  [],
    modified_edges: [],
    summary:        '',
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// TOBS-03: Diff highlight classification tests
// ---------------------------------------------------------------------------

describe('computeDiffHighlights', () => {
  it('marks added nodes as added in highlight map', () => {
    const diff = emptyDiff({
      added_nodes: [{ id: 'worker', level: 3, intent: 'Execute', risk_level: 'low' }],
    });

    const result = computeDiffHighlights(diff);

    expect(result.nodes['worker']).toBe('added');
    expect(Object.keys(result.nodes)).toHaveLength(1);
  });

  it('marks removed nodes as removed in highlight map', () => {
    const diff = emptyDiff({
      removed_nodes: [{ id: 'reviewer', level: 2, intent: 'Review PRs', risk_level: 'medium' }],
    });

    const result = computeDiffHighlights(diff);

    expect(result.nodes['reviewer']).toBe('removed');
    expect(Object.keys(result.nodes)).toHaveLength(1);
  });

  it('marks modified nodes as modified in highlight map', () => {
    const diff = emptyDiff({
      modified_nodes: [{ id: 'coord', changes: { risk_level: { old: 'low', new: 'high' } } }],
    });

    const result = computeDiffHighlights(diff);

    expect(result.nodes['coord']).toBe('modified');
    expect(Object.keys(result.nodes)).toHaveLength(1);
  });

  it('returns empty maps for empty diff', () => {
    const result = computeDiffHighlights(emptyDiff());

    expect(Object.keys(result.nodes)).toHaveLength(0);
    expect(Object.keys(result.edges)).toHaveLength(0);
  });

  it('marks added edges as added in highlight map', () => {
    const diff = emptyDiff({
      added_edges: [{ from_role: 'orchestrator', to_role: 'worker', edge_type: 'delegation' }],
    });

    const result = computeDiffHighlights(diff);

    expect(result.edges['orchestrator->worker']).toBe('added');
  });

  it('marks removed edges as removed in highlight map', () => {
    const diff = emptyDiff({
      removed_edges: [{ from_role: 'pm', to_role: 'dev', edge_type: 'coordination' }],
    });

    const result = computeDiffHighlights(diff);

    expect(result.edges['pm->dev']).toBe('removed');
  });

  it('handles combined added, removed, and modified nodes simultaneously', () => {
    const diff = emptyDiff({
      added_nodes:    [{ id: 'new-agent', level: 3, intent: 'New', risk_level: 'low' }],
      removed_nodes:  [{ id: 'old-agent', level: 2, intent: 'Old', risk_level: 'high' }],
      modified_nodes: [{ id: 'changed', changes: {} }],
    });

    const result = computeDiffHighlights(diff);

    expect(result.nodes['new-agent']).toBe('added');
    expect(result.nodes['old-agent']).toBe('removed');
    expect(result.nodes['changed']).toBe('modified');
    expect(Object.keys(result.nodes)).toHaveLength(3);
  });
});
