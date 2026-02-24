# Phase 06: Global Context Graph - Research

**Researched:** 2026-02-24
**Domain:** Graph Structures in SQLite, Recursive CTEs, Graph-Aware RAG
**Confidence:** HIGH

## Summary

This research focuses on implementing a Graph structure within the existing SQLite-based Nexus-Sync system. The primary goal is to map relationships between decisions and work items (issues/tasks) to enable cross-project dependency tracking and improved retrieval relevance.

The recommended approach is an **Adjacency List** model for the `edges` table, which is simple to implement in SQLite and highly performant for the scale of data expected in a local-first project brain. We will use **Recursive CTEs** for graph traversal (transitive dependencies) and a **Hybrid Retrieval** strategy for "Graph-Aware" relevance boosting.

**Primary recommendation:** Use a dedicated `edges` table with indexes on both `source_id` and `target_id` to support fast bidirectional traversal, and implement graph expansion during the retrieval phase of the "Catch Me Up" pipeline.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| REAS-03 | Adjacency list schema — Persist bidirectional relationships (edges) | Defined SQLite schema with `source_id`, `target_id`, and `relationship_type` for efficient bidirectional storage. |
| REAS-04 | Transitive dependency lookup — Implement recursive CTEs | Verified SQLite `WITH RECURSIVE` syntax and cycle-handling for ripple effect analysis. |
| REAS-05 | Multi-Project Boost — Scoring engine boost (+0.3) | Researched Graph-Aware RAG strategies (k-hop expansion) to identify and boost related project entities. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `better-sqlite3` | ^11.0.0 | Database Engine | Current project standard, supports Recursive CTEs and JSON1 extension. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|--------------|
| `crypto` | Native | UUID Generation | Creating unique IDs for new edges. |

## Architecture Patterns

### Recommended Project Structure
```
src/
├── lib/
│   └── sync/
│       ├── graph.ts         # NEW: Graph traversal and edge management
│       ├── indexer.ts       # UPDATED: Post-index relationship detection
│       ├── suggestions.ts   # UPDATED: Edge creation on suggestion acceptance
│       └── relevance.ts     # UPDATED: Graph-aware boosting logic
```

### Pattern 1: Adjacency List (Edges Table)
**What:** A table representing directed relationships between entities in the `vector_cache`.
**When to use:** Storing explicit (user-defined) and implicit (detected) links.
**Example:**
```sql
CREATE TABLE IF NOT EXISTS edges (
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    relationship_type TEXT NOT NULL, -- 'blocks', 'implements', 'relates_to', 'duplicates'
    weight REAL DEFAULT 1.0,
    metadata JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (source_id, target_id, relationship_type),
    FOREIGN KEY (source_id) REFERENCES vector_cache(id),
    FOREIGN KEY (target_id) REFERENCES vector_cache(id)
);

CREATE INDEX idx_edges_source ON edges(source_id);
CREATE INDEX idx_edges_target ON edges(target_id);
```

### Pattern 2: Transitive Closure (Ripple Effects)
**What:** Using Recursive CTEs to find all nodes reachable from a starting node.
**When to use:** Assessing the "ripple effect" of a decision change.
**Example:**
```sql
-- Find all items impacted by a change in source_id
WITH RECURSIVE ripple_effects(affected_id, depth) AS (
    SELECT target_id, 1
    FROM edges
    WHERE source_id = ?
    UNION
    SELECT e.target_id, re.depth + 1
    FROM edges e
    JOIN ripple_effects re ON e.source_id = re.affected_id
    WHERE re.depth < 5 -- Safety limit to prevent infinite loops/excessive recursion
)
SELECT * FROM ripple_effects;
```

### Anti-Patterns to Avoid
- **Hard-coding relationships in entity metadata:** Makes traversal expensive and limits bidirectional lookups. Use the `edges` table instead.
- **Deep Recursion without depth limits:** Can cause performance degradation or infinite loops in cyclic graphs.
- **Full Graph Vectorization:** Don't vectorize the graph structure itself; vectorize nodes and use the graph for *reranking* or *context expansion*.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Graph Traversal | Custom JS Loops | SQLite Recursive CTEs | Database-level optimization is significantly faster and handles JOINs better. |
| Complex Pathfinding | A* or Dijkstra | Simple BFS via CTE | For OCCC scale, simple k-hop neighbors are usually sufficient for relevance. |

## Common Pitfalls

### Pitfall 1: Cycles in the Graph
**What goes wrong:** Recursive CTEs can loop infinitely if a cycle exists (A -> B -> A).
**Why it happens:** Standard `UNION ALL` does not check for duplicates.
**How to avoid:** Use `UNION` instead of `UNION ALL` in the CTE, which performs implicit de-duplication, or track visited IDs in a path string.

### Pitfall 2: Relationship Proliferation
**What goes wrong:** Creating too many low-confidence edges creates noise.
**Why it happens:** Auto-detection might link everything to everything.
**How to avoid:** Use a `weight` or `confidence` threshold for implicit edges. Only "Accepted" suggestions should become permanent edges.

## Code Examples

### Graph-Aware Relevance Boosting Logic
```typescript
// Proposed addition to searchContext in vector-store.ts
async function boostByGraph(seeds: VectorRecord[], depth: number = 1): Promise<Map<string, number>> {
    const boosts = new Map<string, number>();
    const seedIds = seeds.map(s => s.id);
    
    // Find neighbors of seeds
    const neighbors = db.prepare(`
        SELECT target_id, source_id, weight 
        FROM edges 
        WHERE source_id IN (${seedIds.map(() => '?').join(',')})
           OR target_id IN (${seedIds.map(() => '?').join(',')})
    `).all(...seedIds, ...seedIds);

    for (const edge of neighbors) {
        const linkedId = seedIds.includes(edge.source_id) ? edge.target_id : edge.source_id;
        boosts.set(linkedId, (boosts.get(linkedId) || 0) + (0.2 * edge.weight));
    }
    
    return boosts;
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Semantic-only RAG | GraphRAG / Knowledge-Graph RAG | 2023-2024 | Drastically improves multi-hop reasoning and context relevance. |
| Separate Graph DB | SQLite + CTEs | - | Reduces infra complexity for local-first apps while maintaining power. |

## Open Questions

1. **Relationship Type Taxonomy**
   - What we know: We need standard types like `blocks` and `relates_to`.
   - What's unclear: Which types provide the most value for "Risk Drift" detection in Phase 7.
   - Recommendation: Start with a small set: `implements`, `blocks`, `relates_to`, `duplicates`, `mentions`.

2. **Bidirectional vs Directed**
   - What we know: Most relationships have directionality.
   - What's unclear: Should we always treat them as bidirectional for retrieval?
   - Recommendation: Store as directed, but traverse both directions during retrieval expansion with different weights.

## Sources

### Primary (HIGH confidence)
- [SQLite Official Docs](https://www.sqlite.org/lang_with.html) - Recursive CTE syntax and behavior.
- [Microsoft GraphRAG Research](https://www.microsoft.com/en-us/research/blog/graphrag-unlocking-llm-discovery-on-narrative-private-data/) - General patterns for graph-enhanced retrieval.

### Secondary (MEDIUM confidence)
- [Edge Table Patterns](https://sqliteforum.com) - Best practices for modeling graphs in relational databases.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Using established project tools.
- Architecture: HIGH - Adjacency list is the standard relational graph model.
- Pitfalls: MEDIUM - Real-world performance at scale needs validation.

**Research date:** 2026-02-24
**Valid until:** 2026-03-24
