import { parseIntent } from './src/lib/sync/intent';

const testQueries = [
  "last week",
  "since Monday",
  "yesterday",
  "from 2023-01-01 to 2023-01-02",
  "what happened today?"
];

console.log(`Current Time: ${new Date().toISOString()}
`);

testQueries.forEach(q => {
  const intent = parseIntent(q, "project-123");
  console.log(`Query: "${q}"`);
  console.log(`  Start: ${intent.timeRange.start}`);
  console.log(`  End:   ${intent.timeRange.end}`);
  console.log(`  Boost: ${intent.boostedProjectId}`);
  console.log('---');
});
