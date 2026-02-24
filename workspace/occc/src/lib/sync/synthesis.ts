import { VectorRecord } from './vector-store';

export interface SynthesisResult {
  stream: AsyncGenerator<string>;
  context: VectorRecord[];
  confidence: 'high' | 'low';
}

/**
 * Synthesizes a natural language timeline from ranked context records.
 * Uses Phi-3 via streaming completion.
 */
export async function synthesizeTimeline(
  query: string,
  records: VectorRecord[]
): Promise<SynthesisResult> {
  // 1. Calculate confidence based on top match score
  // If top score is < 0.4, it's low confidence
  const topScore = records.length > 0 ? (records[0] as any)._score || 0 : 0;
  const confidence = topScore >= 0.4 ? 'high' : 'low';

  if (confidence === 'low' || records.length === 0) {
    return {
      stream: emptyGenerator(),
      context: records,
      confidence: 'low'
    };
  }

  // 2. Build the Synthesis Prompt
  const contextString = records.map((r, i) => {
    const type = r.entity_type === 'decision' ? '[DECISION]' : '[ISSUE]';
    return `${i + 1}. ${type} ${r.content}\nMetadata: ${JSON.stringify(r.metadata)}`;
  }).join('\n\n');

  const prompt = `
You are a project assistant helping a developer "Catch Up" on recent activity.
Your goal is to synthesize the following records into a cohesive, chronological timeline.

User Query: "${query}"

Source Records:
"""
${contextString}
"""

Instructions:
1. Group related updates (e.g., a Slack decision about a Linear issue).
2. Use clear headers for different feature areas or topics.
3. Be concise but include specific outcomes and next steps.
4. For every claim, include a short citation link in parentheses (e.g., [Slack] or [Linear]).
5. Maintain a professional, direct tone.

Synthesized Timeline:
`.trim();

  // 3. Trigger streaming completion
  const { streamCompletion } = await import('../ollama');
  const stream = streamCompletion(prompt, { temperature: 0.2 });

  return {
    stream,
    context: records,
    confidence: 'high'
  };
}

async function* emptyGenerator(): AsyncGenerator<string> {
  // Yield nothing
}
