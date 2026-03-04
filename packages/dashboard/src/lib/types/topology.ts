/**
 * TypeScript interfaces matching the Python topology data model.
 * Source: packages/orchestration/src/openclaw/topology/
 *
 * These are the contracts for the entire Phase 65 topology observability feature.
 * Do not modify field names — they must match the Python serialization format exactly.
 */

// ---------------------------------------------------------------------------
// Core graph types (from topology/models.py)
// ---------------------------------------------------------------------------

export interface TopologyNode {
  id: string;
  level: 1 | 2 | 3;
  intent: string;
  risk_level: 'low' | 'medium' | 'high';
  resource_constraints?: Record<string, unknown>;
  estimated_load?: number;
}

export interface TopologyEdge {
  from_role: string;
  to_role: string;
  edge_type: 'delegation' | 'coordination' | 'review_gate' | 'information_flow' | 'escalation';
}

export interface TopologyGraph {
  project_id: string;
  proposal_id?: string;
  version: number;
  created_at: string;
  metadata?: Record<string, unknown>;
  nodes: TopologyNode[];
  edges: TopologyEdge[];
}

// ---------------------------------------------------------------------------
// Proposal types (from topology/proposal_models.py)
// ---------------------------------------------------------------------------

export interface RubricScore {
  complexity: number;
  coordination_overhead: number;
  risk_containment: number;
  time_to_first_output: number;
  cost_estimate: number;
  preference_fit: number;
  overall_confidence: number;
  key_differentiators: string[];
}

export interface TopologyProposal {
  archetype: 'lean' | 'balanced' | 'robust';
  topology: TopologyGraph;
  delegation_boundaries: string;
  coordination_model: string;
  risk_assessment: string;
  justification: string;
  rubric_score?: RubricScore;
}

export interface ProposalSet {
  proposals: TopologyProposal[];
  assumptions: string[];
  outcome: string;
}

// ---------------------------------------------------------------------------
// Diff types (from topology/diff.py)
// ---------------------------------------------------------------------------

export interface ModifiedNode {
  id: string;
  changes: Record<string, { old: unknown; new: unknown }>;
}

export interface ModifiedEdge {
  from_role: string;
  to_role: string;
  old_edge_type: string;
  new_edge_type: string;
}

export interface TopologyDiff {
  added_nodes: TopologyNode[];
  removed_nodes: TopologyNode[];
  modified_nodes: ModifiedNode[];
  added_edges: TopologyEdge[];
  removed_edges: TopologyEdge[];
  modified_edges: ModifiedEdge[];
  summary: string;
  annotations?: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Changelog types (from topology/storage.py)
// ---------------------------------------------------------------------------

export interface ChangelogAnnotations {
  approved_archetype?: string;
  pushback_note?: string;
  rubric_scores?: Record<string, RubricScore>;
  [key: string]: unknown;
}

export interface ChangelogEntry {
  timestamp: string;
  correction_type: 'initial' | 'soft' | 'hard';
  diff?: TopologyDiff;
  annotations?: ChangelogAnnotations;
}

// ---------------------------------------------------------------------------
// API response types (for dashboard API routes)
// ---------------------------------------------------------------------------

export interface TopologyApiResponse {
  approved: TopologyGraph | null;
  proposals: ProposalSet | null;
  projectId: string;
}

export interface ChangelogApiResponse {
  changelog: ChangelogEntry[];
  projectId: string;
}
