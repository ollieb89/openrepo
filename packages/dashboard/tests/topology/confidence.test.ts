import { describe, it, expect } from 'vitest';
import { transformChangelogToChartData } from '../../src/components/topology/ConfidenceChart';
import type { ChangelogEntry, RubricScore } from '../../src/lib/types/topology';

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function makeRubricScore(overrides: Partial<RubricScore> = {}): RubricScore {
  return {
    complexity: 5,
    coordination_overhead: 5,
    risk_containment: 5,
    time_to_first_output: 5,
    cost_estimate: 5,
    preference_fit: 7,
    overall_confidence: 8,
    key_differentiators: [],
    ...overrides,
  };
}

function makeEntry(
  correction_type: ChangelogEntry['correction_type'],
  rubricScores?: Record<string, RubricScore>,
): ChangelogEntry {
  return {
    timestamp: new Date().toISOString(),
    correction_type,
    annotations: rubricScores ? { rubric_scores: rubricScores } : undefined,
  };
}

// ---------------------------------------------------------------------------
// transformChangelogToChartData tests
// ---------------------------------------------------------------------------

describe('transformChangelogToChartData', () => {
  it('returns empty array for empty changelog', () => {
    expect(transformChangelogToChartData([])).toEqual([]);
  });

  it('skips entries that have no rubric_scores annotation', () => {
    const changelog: ChangelogEntry[] = [
      makeEntry('initial'),               // no rubric_scores
      makeEntry('soft'),                  // no rubric_scores
    ];

    expect(transformChangelogToChartData(changelog)).toEqual([]);
  });

  it('produces one data point per entry that has rubric_scores', () => {
    const scores = {
      lean:     makeRubricScore({ overall_confidence: 6 }),
      balanced: makeRubricScore({ overall_confidence: 7 }),
      robust:   makeRubricScore({ overall_confidence: 8 }),
    };

    const changelog: ChangelogEntry[] = [
      makeEntry('initial', scores),
      makeEntry('soft', scores),
      makeEntry('hard', scores),
    ];

    const data = transformChangelogToChartData(changelog);
    expect(data).toHaveLength(3);
  });

  it('extracts lean, balanced, and robust overall_confidence values correctly', () => {
    const scores = {
      lean:     makeRubricScore({ overall_confidence: 5 }),
      balanced: makeRubricScore({ overall_confidence: 7 }),
      robust:   makeRubricScore({ overall_confidence: 9 }),
    };

    const changelog: ChangelogEntry[] = [makeEntry('initial', scores)];
    const data = transformChangelogToChartData(changelog);

    expect(data).toHaveLength(1);
    expect(data[0].lean).toBe(5);
    expect(data[0].balanced).toBe(7);
    expect(data[0].robust).toBe(9);
  });

  it('assigns sequential event numbers starting from 1', () => {
    const scores = {
      balanced: makeRubricScore({ overall_confidence: 7 }),
    };

    const changelog: ChangelogEntry[] = [
      makeEntry('initial', scores),
      makeEntry('soft', scores),
      makeEntry('hard', scores),
    ];

    const data = transformChangelogToChartData(changelog);
    expect(data[0].event).toBe(1);
    expect(data[1].event).toBe(2);
    expect(data[2].event).toBe(3);
  });

  it('skips entries without rubric_scores resulting in fewer data points than changelog length', () => {
    const scores = {
      lean:     makeRubricScore({ overall_confidence: 6 }),
      balanced: makeRubricScore({ overall_confidence: 7 }),
    };

    const changelog: ChangelogEntry[] = [
      makeEntry('initial'),          // no rubric_scores — skipped
      makeEntry('soft', scores),     // has rubric_scores
      makeEntry('soft'),             // no rubric_scores — skipped
      makeEntry('hard', scores),     // has rubric_scores
    ];

    const data = transformChangelogToChartData(changelog);
    expect(data).toHaveLength(2);   // only 2 entries had rubric_scores
  });

  it('extracts preference_fit from the first available archetype rubric score', () => {
    const scores = {
      lean: makeRubricScore({ overall_confidence: 6, preference_fit: 8 }),
    };

    const changelog: ChangelogEntry[] = [makeEntry('soft', scores)];
    const data = transformChangelogToChartData(changelog);

    expect(data[0].preference_fit).toBe(8);
  });

  it('handles changelog entries with only partial archetype scores', () => {
    // Only balanced — lean and robust should be undefined
    const scores = {
      balanced: makeRubricScore({ overall_confidence: 7 }),
    };

    const changelog: ChangelogEntry[] = [makeEntry('soft', scores)];
    const data = transformChangelogToChartData(changelog);

    expect(data).toHaveLength(1);
    expect(data[0].balanced).toBe(7);
    expect(data[0].lean).toBeUndefined();
    expect(data[0].robust).toBeUndefined();
  });
});
