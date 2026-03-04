import { describe, it, expect } from 'vitest';
import { sortChangelog, extractDiffLines } from '../../src/components/topology/CorrectionTimeline';
import type { ChangelogEntry, TopologyDiff } from '../../src/lib/types/topology';

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function makeEntry(
  timestamp: string,
  correction_type: ChangelogEntry['correction_type'] = 'soft',
  diff?: TopologyDiff,
): ChangelogEntry {
  return { timestamp, correction_type, diff };
}

const EMPTY_DIFF: TopologyDiff = {
  added_nodes: [],
  removed_nodes: [],
  modified_nodes: [],
  added_edges: [],
  removed_edges: [],
  modified_edges: [],
  summary: 'no changes',
};

// ---------------------------------------------------------------------------
// sortChangelog tests
// ---------------------------------------------------------------------------

describe('sortChangelog', () => {
  it('sorts out-of-order entries by timestamp ascending (oldest first)', () => {
    const entries: ChangelogEntry[] = [
      makeEntry('2024-03-10T12:00:00Z'),
      makeEntry('2024-01-01T00:00:00Z'),
      makeEntry('2024-06-15T08:30:00Z'),
    ];

    const sorted = sortChangelog(entries);

    expect(sorted[0].timestamp).toBe('2024-01-01T00:00:00Z');
    expect(sorted[1].timestamp).toBe('2024-03-10T12:00:00Z');
    expect(sorted[2].timestamp).toBe('2024-06-15T08:30:00Z');
  });

  it('returns a new array (does not mutate the original)', () => {
    const entries: ChangelogEntry[] = [
      makeEntry('2024-02-01T00:00:00Z'),
      makeEntry('2024-01-01T00:00:00Z'),
    ];
    const original = [...entries];
    sortChangelog(entries);
    expect(entries[0].timestamp).toBe(original[0].timestamp);
  });

  it('returns the same single entry unchanged', () => {
    const entries: ChangelogEntry[] = [makeEntry('2024-05-01T00:00:00Z', 'initial')];
    const sorted = sortChangelog(entries);
    expect(sorted).toHaveLength(1);
    expect(sorted[0].correction_type).toBe('initial');
  });

  it('handles an empty array gracefully', () => {
    expect(sortChangelog([])).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// extractDiffLines tests
// ---------------------------------------------------------------------------

describe('extractDiffLines', () => {
  it('returns empty array when diff is undefined', () => {
    expect(extractDiffLines(undefined)).toEqual([]);
  });

  it('returns empty array when diff is null', () => {
    expect(extractDiffLines(null)).toEqual([]);
  });

  it('returns empty array when diff has no changes', () => {
    expect(extractDiffLines(EMPTY_DIFF)).toEqual([]);
  });

  it('produces "added" type lines for added_nodes with correct text format', () => {
    const diff: TopologyDiff = {
      ...EMPTY_DIFF,
      added_nodes: [
        { id: 'orchestrator', level: 1, intent: 'direct work', risk_level: 'low' },
        { id: 'specialist', level: 3, intent: 'execute task', risk_level: 'medium' },
      ],
    };

    const lines = extractDiffLines(diff);
    expect(lines).toHaveLength(2);
    expect(lines[0]).toEqual({ type: 'added', text: '+ orchestrator (node)' });
    expect(lines[1]).toEqual({ type: 'added', text: '+ specialist (node)' });
  });

  it('produces "removed" type lines for removed_nodes', () => {
    const diff: TopologyDiff = {
      ...EMPTY_DIFF,
      removed_nodes: [
        { id: 'old-agent', level: 2, intent: 'deprecated', risk_level: 'high' },
      ],
    };

    const lines = extractDiffLines(diff);
    expect(lines).toHaveLength(1);
    expect(lines[0]).toEqual({ type: 'removed', text: '- old-agent (node)' });
  });

  it('produces "modified" type lines for modified_nodes', () => {
    const diff: TopologyDiff = {
      ...EMPTY_DIFF,
      modified_nodes: [
        { id: 'pm-agent', changes: { risk_level: { old: 'low', new: 'medium' } } },
      ],
    };

    const lines = extractDiffLines(diff);
    expect(lines).toHaveLength(1);
    expect(lines[0]).toEqual({ type: 'modified', text: '~ pm-agent (node)' });
  });

  it('produces edge diff lines with "from_role -> to_role (edge)" format', () => {
    const diff: TopologyDiff = {
      ...EMPTY_DIFF,
      added_edges: [{ from_role: 'pm', to_role: 'worker', edge_type: 'delegation' }],
      removed_edges: [{ from_role: 'lead', to_role: 'qa', edge_type: 'review_gate' }],
    };

    const lines = extractDiffLines(diff);
    expect(lines).toHaveLength(2);
    expect(lines[0]).toEqual({ type: 'added', text: '+ pm -> worker (edge)' });
    expect(lines[1]).toEqual({ type: 'removed', text: '- lead -> qa (edge)' });
  });

  it('handles mixed adds, removes, and modifies in correct order', () => {
    const diff: TopologyDiff = {
      added_nodes: [{ id: 'new-node', level: 2, intent: 'new', risk_level: 'low' }],
      removed_nodes: [{ id: 'old-node', level: 3, intent: 'old', risk_level: 'low' }],
      modified_nodes: [{ id: 'changed-node', changes: {} }],
      added_edges: [{ from_role: 'a', to_role: 'b', edge_type: 'coordination' }],
      removed_edges: [{ from_role: 'c', to_role: 'd', edge_type: 'escalation' }],
      modified_edges: [{ from_role: 'e', to_role: 'f', old_edge_type: 'delegation', new_edge_type: 'review_gate' }],
      summary: 'mixed changes',
    };

    const lines = extractDiffLines(diff);
    expect(lines).toHaveLength(6);

    const types = lines.map((l) => l.type);
    expect(types).toContain('added');
    expect(types).toContain('removed');
    expect(types).toContain('modified');
  });
});
