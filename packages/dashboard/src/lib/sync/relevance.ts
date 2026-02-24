import { VectorRecord } from './vector-store';

export interface ScoringResult {
  score: number;
  reasons: string[];
}

/**
 * Calculates a relevance score (0.0 to 1.0) between a decision and an issue.
 * 
 * Signals:
 * - Explicit Mention: Search for issue ID in decision text (Boost to 0.95)
 * - Semantic Similarity: Cosine similarity of embeddings
 * - Keyword Overlap: Shared technical keywords
 * - Temporal Proximity: Created within 48 hours
 */
export function calculateScore(decision: VectorRecord, issue: VectorRecord): ScoringResult {
  let score = 0;
  const reasons: Set<string> = new Set();

  // 1. Explicit Mention (GH-123, LIN-45, etc.)
  // We check if the issue ID exists as a whole word in the decision content
  const idRegex = new RegExp(`\\b${issue.id}\\b`, 'i');
  if (idRegex.test(decision.content)) {
    score = 0.95;
    reasons.add('explicit_mention');
  }

  // 2. Semantic Similarity
  if (decision.embedding && issue.embedding) {
    const similarity = cosineSimilarity(decision.embedding, issue.embedding);
    const semanticScore = Math.max(0, similarity);
    
    // Use semantic score if it's higher than current score
    if (semanticScore > score) {
      score = semanticScore;
    }
    
    if (semanticScore > 0.6) {
      reasons.add('semantic_similarity');
    }
  }

  // 3. Keyword Overlap
  const decisionKeywords = extractKeywords(decision.content);
  const issueKeywords = extractKeywords(issue.content);
  const overlap = decisionKeywords.filter(k => issueKeywords.includes(k));
  
  if (overlap.length > 0) {
    const keywordScore = Math.min(0.5, overlap.length * 0.1);
    if (keywordScore > score) {
      score = keywordScore;
    }
    reasons.add('keyword_overlap');
  }

  // 4. Temporal Proximity
  const decisionTime = getTime(decision);
  const issueTime = getTime(issue);
  
  if (decisionTime > 0 && issueTime > 0) {
    const diff = Math.abs(decisionTime - issueTime);
    const fortyEightHours = 48 * 60 * 60 * 1000;
    if (diff < fortyEightHours) {
      // Temporal proximity is a boost, not a base score
      score += 0.1;
      reasons.add('temporal_proximity');
    }
  }

  return {
    score: Math.min(1.0, score),
    reasons: Array.from(reasons)
  };
}

function cosineSimilarity(v1: number[], v2: number[]) {
  if (v1.length !== v2.length || v1.length === 0) return 0;
  let dotProduct = 0;
  let norm1 = 0;
  let norm2 = 0;
  for (let i = 0; i < v1.length; i++) {
    dotProduct += v1[i] * v2[i];
    norm1 += v1[i] * v1[i];
    norm2 += v2[i] * v2[i];
  }
  return dotProduct / (Math.sqrt(norm1) * Math.sqrt(norm2));
}

function extractKeywords(text: string): string[] {
  const TECH_KEYWORDS = [
    'api', 'database', 'frontend', 'backend', 'auth', 'security', 'privacy',
    'sync', 'vector', 'embedding', 'docker', 'container', 'ui', 'ux',
    'performance', 'scalability', 'react', 'nextjs', 'typescript', 'sqlite',
    'vss', 'search', 'index', 'summary', 'decision', 'issue', 'link',
    'suggestion', 'review', 'loop', 'autonomous', 'agent', 'executor'
  ];
  const words = text.toLowerCase().split(/\W+/);
  return Array.from(new Set(words.filter(w => TECH_KEYWORDS.includes(w))));
}

function getTime(record: VectorRecord): number {
  if (record.metadata?.created_at) return new Date(record.metadata.created_at).getTime();
  if (record.metadata?.timestamp) return new Date(record.metadata.timestamp).getTime();
  return 0;
}
