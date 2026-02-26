#!/bin/bash
set -e
DB="workspace/.openclaw/nexus-sync.db"

# Seed test data
sqlite3 $DB "INSERT INTO vector_cache (id, entity_type, content) VALUES ('A', 'test_node', 'Node A') ON CONFLICT DO NOTHING;"
sqlite3 $DB "INSERT INTO vector_cache (id, entity_type, content) VALUES ('B', 'test_node', 'Node B') ON CONFLICT DO NOTHING;"
sqlite3 $DB "INSERT INTO vector_cache (id, entity_type, content) VALUES ('C', 'test_node', 'Node C') ON CONFLICT DO NOTHING;"
sqlite3 $DB "INSERT INTO vector_cache (id, entity_type, content) VALUES ('D', 'test_node', 'Node D') ON CONFLICT DO NOTHING;"

sqlite3 $DB "INSERT INTO edges (source_id, target_id, relationship_type) VALUES ('A', 'B', 'test_ripple') ON CONFLICT DO NOTHING;"
sqlite3 $DB "INSERT INTO edges (source_id, target_id, relationship_type) VALUES ('B', 'C', 'test_ripple') ON CONFLICT DO NOTHING;"
sqlite3 $DB "INSERT INTO edges (source_id, target_id, relationship_type) VALUES ('C', 'A', 'test_ripple') ON CONFLICT DO NOTHING;"
sqlite3 $DB "INSERT INTO edges (source_id, target_id, relationship_type) VALUES ('A', 'D', 'test_ripple') ON CONFLICT DO NOTHING;"

echo "Running recursive CTE query..."
RES=$(sqlite3 $DB "
WITH RECURSIVE ripple(id, depth) AS (
  SELECT 'A' as id, 0 as depth
  UNION
  SELECT e.target_id, r.depth + 1
  FROM edges e
  JOIN ripple r ON e.source_id = r.id
  WHERE r.depth < 5
)
SELECT id FROM ripple WHERE depth > 0 GROUP BY id;
")

echo "Result: $RES"

# Check if result contains B, C, D and not too many items (due to cycles)
COUNT=$(echo "$RES" | wc -l)
echo "Count: $COUNT"

if echo "$RES" | grep -q "B" && echo "$RES" | grep -q "C" && echo "$RES" | grep -q "D" && [ $COUNT -eq 3 ]; then
  echo "SUCCESS: Ripple effects found correctly."
else
  echo "FAILURE: Ripple effects incorrect."
  exit 1
fi

# Cleanup
sqlite3 $DB "DELETE FROM edges WHERE relationship_type = 'test_ripple';"
sqlite3 $DB "DELETE FROM vector_cache WHERE entity_type = 'test_node';"
