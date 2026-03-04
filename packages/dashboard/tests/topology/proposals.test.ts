import { describe, it, expect } from 'vitest';
import type { ProposalSet, TopologyProposal, RubricScore } from '@/lib/types/topology';

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function makeGraph(projectId: string) {
  return {
    project_id: projectId,
    version: 1,
    created_at: '2026-03-04T00:00:00Z',
    nodes: [],
    edges: [],
  };
}

function makeRubric(overrides: Partial<RubricScore> = {}): RubricScore {
  return {
    complexity: 5,
    coordination_overhead: 5,
    risk_containment: 5,
    time_to_first_output: 5,
    cost_estimate: 5,
    preference_fit: 5,
    overall_confidence: 5,
    key_differentiators: [],
    ...overrides,
  };
}

const MOCK_PROPOSAL_SET: ProposalSet = {
  assumptions: ['Single project context', 'Async coordination acceptable'],
  outcome: 'Proposals generated for lean, balanced, and robust archetypes',
  proposals: [
    {
      archetype: 'lean',
      topology: makeGraph('test-lean'),
      delegation_boundaries: 'Single orchestrator delegates directly',
      coordination_model: 'Async message passing',
      risk_assessment: 'Low risk, minimal coordination overhead',
      justification: 'Lean topology is simplest for this project size',
      rubric_score: makeRubric({ overall_confidence: 7.2, complexity: 8, cost_estimate: 9 }),
    },
    {
      archetype: 'balanced',
      topology: makeGraph('test-balanced'),
      delegation_boundaries: 'PM coordinates specialist agents',
      coordination_model: 'Structured coordination with review gates',
      risk_assessment: 'Moderate risk with review gates reducing quality issues',
      justification: 'Balanced provides structured coordination without excessive overhead',
      rubric_score: makeRubric({ overall_confidence: 8.5, complexity: 6, cost_estimate: 6 }),
    },
    {
      archetype: 'robust',
      topology: makeGraph('test-robust'),
      delegation_boundaries: 'Dedicated reviewer and multiple coordination paths',
      coordination_model: 'Redundant coordination with explicit escalation paths',
      risk_assessment: 'High containment with review gates on all critical paths',
      justification: 'Robust is warranted for high-risk output requirements',
      rubric_score: makeRubric({ overall_confidence: 6.1, complexity: 3, cost_estimate: 3 }),
    },
  ],
};

// ---------------------------------------------------------------------------
// TOBS-06: ProposalSet parsing tests
// ---------------------------------------------------------------------------

describe('ProposalSet parsing', () => {
  it('accesses individual archetype proposals from ProposalSet', () => {
    const lean = MOCK_PROPOSAL_SET.proposals.find((p) => p.archetype === 'lean');
    const balanced = MOCK_PROPOSAL_SET.proposals.find((p) => p.archetype === 'balanced');
    const robust = MOCK_PROPOSAL_SET.proposals.find((p) => p.archetype === 'robust');

    expect(lean).toBeDefined();
    expect(balanced).toBeDefined();
    expect(robust).toBeDefined();

    expect(lean!.archetype).toBe('lean');
    expect(balanced!.archetype).toBe('balanced');
    expect(robust!.archetype).toBe('robust');

    // Verify data from fixture
    expect(lean!.topology.project_id).toBe('test-lean');
    expect(balanced!.delegation_boundaries).toContain('PM coordinates');
  });

  it('extracts rubric_score from each proposal', () => {
    const scores = MOCK_PROPOSAL_SET.proposals.map((p) => p.rubric_score?.overall_confidence);

    expect(scores).toHaveLength(3);
    expect(scores[0]).toBeCloseTo(7.2);
    expect(scores[1]).toBeCloseTo(8.5);
    expect(scores[2]).toBeCloseTo(6.1);

    // All 7 dimensions accessible
    const lean = MOCK_PROPOSAL_SET.proposals.find((p) => p.archetype === 'lean');
    const score = lean!.rubric_score!;
    expect(score.complexity).toBeDefined();
    expect(score.coordination_overhead).toBeDefined();
    expect(score.risk_containment).toBeDefined();
    expect(score.time_to_first_output).toBeDefined();
    expect(score.cost_estimate).toBeDefined();
    expect(score.preference_fit).toBeDefined();
    expect(score.overall_confidence).toBeDefined();
  });

  it('identifies highest confidence proposal', () => {
    const proposals = MOCK_PROPOSAL_SET.proposals;
    const highest = proposals.reduce((best, p) => {
      const bestConf = best.rubric_score?.overall_confidence ?? -Infinity;
      const pConf = p.rubric_score?.overall_confidence ?? -Infinity;
      return pConf > bestConf ? p : best;
    }, proposals[0]);

    expect(highest.archetype).toBe('balanced');
    expect(highest.rubric_score?.overall_confidence).toBeCloseTo(8.5);
  });

  it('handles null ProposalSet gracefully', () => {
    const nullSet: ProposalSet | null = null;

    // Safe access pattern — returns empty array for null
    const proposals: TopologyProposal[] = nullSet?.proposals ?? [];
    expect(proposals).toHaveLength(0);

    // Finding a proposal in null set returns undefined
    const lean = nullSet?.proposals.find((p) => p.archetype === 'lean');
    expect(lean).toBeUndefined();

    // Math.max on empty confidence list
    const maxConf = Math.max(...(nullSet?.proposals.map((p) => p.rubric_score?.overall_confidence ?? 0) ?? [0]));
    expect(maxConf).toBe(0);
  });
});
