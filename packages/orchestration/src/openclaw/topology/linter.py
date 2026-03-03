"""
Topology Proposal Constraint Linter

Validates topology proposals against the AgentRegistry (known roles) and pool
concurrency limits (max_concurrent). Auto-constrains pool violations by reducing
parallel L3 count while preferring to preserve review-gate edges.

Roles unknown to the registry are rejected immediately (valid=False).
Pool violations are auto-adjusted (valid=True, adjusted=True) with transparent
descriptions of each change in the adjustments list.

Design decisions (from 62-RESEARCH.md):
- Prefer removing coordination-only L3 roles before review-gate-connected ones
  (Pitfall 3: review gates are the safety net — never silently drop them).
- If removing any role would eliminate ALL review gates, emit a WARNING in
  adjustments so the user knows the adjusted topology is less safe.
- MAX_RETRIES = 2 (3 total attempts total) — callers may retry generation.
"""

from dataclasses import dataclass, field
from typing import List, Set, Tuple

from openclaw.agent_registry import AgentRegistry

# Total attempts = MAX_RETRIES + 1
MAX_RETRIES: int = 2


@dataclass
class LintResult:
    """
    Result of linting a single topology proposal.

    valid:          True if all roles are known and no unfixable violations exist.
                    False if any roles are not in the registry.
    adjusted:       True if the proposal was auto-modified (e.g., pool reduction).
    rejected_roles: List of role IDs that were not found in the registry.
    adjustments:    Human-readable descriptions of each auto-adjustment applied.
    proposal:       The (possibly adjusted) proposal dict.
    """

    valid: bool
    adjusted: bool
    rejected_roles: List[str]
    adjustments: List[str]
    proposal: dict


class ConstraintLinter:
    """
    Validates topology proposals and auto-adjusts pool violations.

    Usage:
        linter = ConstraintLinter(registry=agent_registry, max_concurrent=3)
        result = linter.lint("lean", proposal_dict)

    proposal_dict structure expected:
        {
            "roles": [{"id": str, "level": int}, ...],
            "edges": [{"from": str, "to": str, "type": str}, ...],
        }
    """

    def __init__(self, registry: AgentRegistry, max_concurrent: int):
        self.registry = registry
        self.max_concurrent = max_concurrent
        # Cache known role IDs for O(1) lookup
        self._known_roles: Set[str] = set(registry._agents.keys())

    def lint(self, archetype: str, proposal_data: dict) -> LintResult:
        """
        Validate and auto-adjust a single archetype proposal.

        Steps:
        1. Check all role IDs against registry — reject if any unknown.
        2. Count level-3 roles — auto-constrain if > max_concurrent.
        3. Return clean LintResult if both checks pass.

        Args:
            archetype: "lean", "balanced", or "robust" (informational, not validated).
            proposal_data: Proposal dict with "roles" and "edges" keys.

        Returns:
            LintResult with full status information.
        """
        roles = proposal_data.get("roles", [])

        # --- Step 1: Role registry check ---
        unknown = [r["id"] for r in roles if r.get("id") not in self._known_roles]
        if unknown:
            return LintResult(
                valid=False,
                adjusted=False,
                rejected_roles=unknown,
                adjustments=[],
                proposal=proposal_data,
            )

        # --- Step 2: Pool concurrency check ---
        l3_roles = [r for r in roles if r.get("level") == 3]
        if len(l3_roles) > self.max_concurrent:
            adjusted_proposal, adj_log = self._auto_constrain(proposal_data, l3_roles)
            return LintResult(
                valid=True,
                adjusted=True,
                rejected_roles=[],
                adjustments=adj_log,
                proposal=adjusted_proposal,
            )

        # --- All checks passed ---
        return LintResult(
            valid=True,
            adjusted=False,
            rejected_roles=[],
            adjustments=[],
            proposal=proposal_data,
        )

    # -------------------------------------------------------------------------
    # Internal: auto-constraining
    # -------------------------------------------------------------------------

    def _auto_constrain(
        self,
        proposal_data: dict,
        l3_roles: List[dict],
    ) -> Tuple[dict, List[str]]:
        """
        Reduce parallel L3 role count to max_concurrent.

        Strategy:
        1. Score each L3 role by "removal cost" — roles connected to review_gate
           edges have high cost, roles with only coordination edges have low cost.
        2. Remove lowest-cost roles first (excess = len(l3_roles) - max_concurrent).
        3. For each removed role, also remove edges referencing it.
        4. If removing would eliminate ALL review-gate edges, emit a WARNING.

        Returns:
            (adjusted_proposal_dict, list_of_adjustment_descriptions)
        """
        import copy
        proposal = copy.deepcopy(proposal_data)
        edges = proposal.get("edges", [])
        roles = proposal.get("roles", [])

        excess = len(l3_roles) - self.max_concurrent
        adj_log: List[str] = []

        # Map role_id -> removal cost (higher = keep it)
        role_cost = self._compute_removal_costs(l3_roles, edges)

        # Sort by cost ascending (cheapest to remove first)
        sorted_l3 = sorted(l3_roles, key=lambda r: role_cost.get(r["id"], 0))

        # Identify current review-gate-connected roles before removal
        review_gate_roles = self._get_review_gate_role_ids(edges)
        initial_review_gate_count = len(
            [e for e in edges if e.get("type") == "review_gate"]
        )

        roles_to_remove: Set[str] = set()
        for role in sorted_l3[:excess]:
            roles_to_remove.add(role["id"])

        # Check if removal removes any review gate edges
        # Warn if ALL review gates are lost — the adjusted topology loses its safety net.
        # Also warn if more than half of review gates are lost (significant safety reduction).
        remaining_review_edges = [
            e for e in edges
            if e.get("type") == "review_gate"
            and e.get("from") not in roles_to_remove
            and e.get("to") not in roles_to_remove
        ]
        removed_review_count = initial_review_gate_count - len(remaining_review_edges)
        if initial_review_gate_count > 0 and removed_review_count > 0:
            if len(remaining_review_edges) == 0:
                adj_log.append(
                    f"WARNING: Removing {len(roles_to_remove)} role(s) eliminates all "
                    f"{initial_review_gate_count} review gate edge(s). "
                    "Adjusted topology has no safety gates."
                )
            else:
                adj_log.append(
                    f"WARNING: Removing {len(roles_to_remove)} role(s) reduces review gates "
                    f"from {initial_review_gate_count} to {len(remaining_review_edges)}. "
                    "Adjusted topology has reduced safety."
                )

        # Apply role removals
        proposal["roles"] = [r for r in roles if r.get("id") not in roles_to_remove]

        # Remove edges referencing removed roles
        proposal["edges"] = [
            e for e in edges
            if e.get("from") not in roles_to_remove
            and e.get("to") not in roles_to_remove
        ]

        # Log the adjustment
        adj_log.append(
            f"Adjusted: {len(l3_roles)} parallel L3 role(s) reduced to "
            f"{self.max_concurrent} (max_concurrent limit). "
            f"Removed: {sorted(roles_to_remove)}."
        )

        return proposal, adj_log

    def _compute_removal_costs(
        self,
        l3_roles: List[dict],
        edges: List[dict],
    ) -> dict:
        """
        Assign a removal cost (0=cheap, high=expensive) to each L3 role.

        Cost rules:
        - Each review_gate edge connected to the role adds 10 to its cost.
        - Each coordination edge connected to the role adds 1 to its cost.
        - Delegation edges: no cost (removing a leaf L3 from delegation is cheap).

        Returns:
            Dict of role_id -> int cost.
        """
        costs: dict = {r["id"]: 0 for r in l3_roles}
        l3_ids = set(costs.keys())

        for edge in edges:
            from_role = edge.get("from", "")
            to_role = edge.get("to", "")
            edge_type = edge.get("type", "")

            if edge_type == "review_gate":
                # High cost: review gate roles are valuable
                if from_role in l3_ids:
                    costs[from_role] = costs.get(from_role, 0) + 10
                if to_role in l3_ids:
                    costs[to_role] = costs.get(to_role, 0) + 10
            elif edge_type == "coordination":
                # Low cost: coordination roles can be merged
                if from_role in l3_ids:
                    costs[from_role] = costs.get(from_role, 0) + 1
                if to_role in l3_ids:
                    costs[to_role] = costs.get(to_role, 0) + 1

        return costs

    def _get_review_gate_role_ids(self, edges: List[dict]) -> Set[str]:
        """Return the set of role IDs that have at least one review_gate edge."""
        result: Set[str] = set()
        for edge in edges:
            if edge.get("type") == "review_gate":
                if edge.get("from"):
                    result.add(edge["from"])
                if edge.get("to"):
                    result.add(edge["to"])
        return result
