import { generateCompletion } from '../ollama';
import type { ThreadRecord, Decision } from '../types/decisions';
import { loadSyncRecords, loadDecisions, saveDecisions } from './storage';
import { indexEntity } from './indexer';
import { generateSuggestions } from './suggestions';

/**
 * Extracts decisions from a single Slack thread using Phi-3.
 */
export async function extractDecisionsFromThread(
  thread: ThreadRecord, 
  connectorId: string, 
  sourceId: string, 
  hint?: string
): Promise<Decision[]> {
  const hintSection = hint ? `\n\nUSER HINT: ${hint}\n(Please incorporate this hint into your analysis.)` : '';
  const prompt = `
Analyze the following Slack thread to extract key decisions. 
A decision is a consensus reached, a resolution to a debate, or a clear path forward.

Thread Content:
"""
${thread.payload.text}
"""${hintSection}

Think step-by-step:
1. Analyze the thread for proposals and debate.
2. Identify consensus (Convergent Evolution).
3. Extract the final Outcome.
4. Identify Participants (@mentions).
5. Extract Next Steps.
6. Find the "Smoking Gun" citation: the EXACT quote from the thread that confirms the decision.

Return your findings in the following format:
DECISION_START
Outcome: [Summary of the decision]
Participants: [List of @mentions, e.g. <@U12345>]
Next Steps: [Action items or "None"]
Citation: [Exact quote from the thread]
DECISION_END

If multiple decisions were made, provide multiple blocks. If no decision was made, return "NO_DECISION".
`.trim();

  const response = await generateCompletion(prompt, { temperature: 0 });

  if (response.includes('NO_DECISION')) {
    return [];
  }

  const decisions: Decision[] = [];
  const blocks = response.split('DECISION_START').filter(b => b.includes('DECISION_END'));

  for (const block of blocks) {
    const outcome = block.match(/Outcome:\s*(.*)/)?.[1]?.trim();
    const participantsRaw = block.match(/Participants:\s*(.*)/)?.[1]?.trim() || '';
    const nextSteps = block.match(/Next Steps:\s*(.*)/)?.[1]?.trim();
    const citation = block.match(/Citation:\s*(.*)/)?.[1]?.trim();

    if (!outcome || !citation) continue;

    // Entity Hoisting: Extract Slack mentions and Linear IDs
    const slackMentionRegex = /<@U[A-Z0-9]+>/g;
    const participants = Array.from(new Set(participantsRaw.match(slackMentionRegex) || []));

    const linearIdRegex = /\b[A-Z0-9]{2,}-\d+\b/g;
    const linearIds = Array.from(new Set(block.match(linearIdRegex) || []));

    // Validation: Ensure citation exists in source text (prevent hallucinations)
    // We remove potential markdown or extra quotes the LLM might have added to the citation
    const cleanCitation = citation.replace(/^["']|["']$/g, '');
    
    if (!thread.payload.text.includes(cleanCitation)) {
      console.warn(`[Summarizer] Citation validation failed for thread ${thread.id}. Skipping decision block.`);
      continue;
    }

    const now = new Date().toISOString();
    decisions.push({
      id: crypto.randomUUID(),
      threadId: thread.id,
      connectorId,
      sourceId,
      outcome,
      participants,
      nextStep: (!nextSteps || nextSteps === 'None') ? null : nextSteps,
      citation: cleanCitation,
      linearIds,
      isHidden: false,
      createdAt: now,
      updatedAt: now,
    });
  }

  return decisions;
}

/**
 * Background runner that processes new records for a given source and generates decisions.
 */
export async function processNewRecords(connectorId: string, sourceId: string): Promise<void> {
  // 1. Load ThreadRecords from storage.
  // In our system, all sync records for Slack are treated as summarizable threads.
  const records = await loadSyncRecords(connectorId, sourceId) as ThreadRecord[];
  
  if (records.length === 0) return;

  // 2. Filter for records that haven't been summarized yet.
  const existingDecisions = await loadDecisions(connectorId);
  const summarizedThreadIds = new Set(existingDecisions.map(d => d.threadId));
  
  const newThreads = records.filter(r => !summarizedThreadIds.has(r.id));
  
  if (newThreads.length === 0) {
    console.log(`[Summarizer] No new threads to process for ${connectorId}::${sourceId}`);
    return;
  }

  console.log(`[Summarizer] Processing ${newThreads.length} new threads for ${connectorId}::${sourceId}`);

  const allNewDecisions: Decision[] = [];

  for (const thread of newThreads) {
    try {
      const threadDecisions = await extractDecisionsFromThread(thread, connectorId, sourceId);
      allNewDecisions.push(...threadDecisions);
    } catch (error) {
      console.error(`[Summarizer] Failed to process thread ${thread.id}:`, error);
    }
  }

  // 4. Persist resulting Decision objects.
  if (allNewDecisions.length > 0) {
    await saveDecisions(connectorId, allNewDecisions);
    console.log(`[Summarizer] Saved ${allNewDecisions.length} new decisions for ${connectorId}`);

    // 5. Index decisions for semantic search (Phase 4)
    for (const decision of allNewDecisions) {
      // Content for indexing is the outcome + citation
      const indexContent = `${decision.outcome}\n\nCitation: ${decision.citation}`;
      indexEntity(decision.id, 'decision', indexContent, {
        connectorId: decision.connectorId,
        sourceId: decision.sourceId,
        threadId: decision.threadId,
      }).then(() => {
        // Trigger suggestion generation after indexing is done
        return generateSuggestions(decision.id);
      }).catch(err => {
        console.error(`[Summarizer] Failed to index or suggest for decision ${decision.id}:`, err);
      });
    }
  } else {
    console.log(`[Summarizer] No decisions extracted from ${newThreads.length} threads.`);
  }
}
