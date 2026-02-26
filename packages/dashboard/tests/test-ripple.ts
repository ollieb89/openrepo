import { findRippleEffects, addEdge } from '../src/lib/sync/graph';
import Database from 'better-sqlite3';
import path from 'path';
import fs from 'fs';

const DB_PATH = path.join(process.cwd(), 'workspace', '.openclaw', 'nexus-sync.db');

async function test() {
  const db = new Database(DB_PATH);
  
  // Cleanup
  db.prepare("DELETE FROM edges WHERE relationship_type = 'test_ripple'").run();
  db.prepare("DELETE FROM vector_cache WHERE entity_type = 'test_node'").run();
  
  // Seed nodes
  const insertNode = db.prepare('INSERT INTO vector_cache (id, entity_type, content) VALUES (?, ?, ?)');
  insertNode.run('A', 'test_node', 'Node A');
  insertNode.run('B', 'test_node', 'Node B');
  insertNode.run('C', 'test_node', 'Node C');
  insertNode.run('D', 'test_node', 'Node D');
  
  // Seed edges: A -> B -> C, C -> A (cycle), A -> D
  addEdge('A', 'B', 'test_ripple');
  addEdge('B', 'C', 'test_ripple');
  addEdge('C', 'A', 'test_ripple');
  addEdge('A', 'D', 'test_ripple');
  
  console.log('Ripple effects from A:');
  const rippleA = findRippleEffects('A', 5);
  console.log(JSON.stringify(rippleA, null, 2));
  
  const ids = rippleA.map(r => r.id);
  const expected = ['B', 'C', 'D'];
  const pass = expected.every(id => ids.includes(id)) && ids.length === 3;
  
  if (pass) {
    console.log('SUCCESS: Ripple effects found correctly and terminated on cycle.');
  } else {
    console.error('FAILURE: Ripple effects incorrect.');
    console.error('Found:', ids);
    console.error('Expected:', expected);
    process.exit(1);
  }
}

test().catch(err => {
  console.error(err);
  process.exit(1);
});
