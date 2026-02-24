import type { SyncRecord } from "../sync/engine";

/**
 * ThreadRecord extends basic SyncRecord to require fields needed for summarization.
 * Specifically for Slack threads, these fields are expected in the payload.
 */
export interface ThreadRecord extends SyncRecord {
  payload: {
    text: string;
    user: string;
    messageTs: string;
    channelId: string;
    [key: string]: unknown;
  };
}

/**
 * Decision represents an extracted outcome from one or more threads.
 */
export interface Decision {
  id: string;
  threadId: string; // source reference (can be a Slack thread TS or a unique record ID)
  connectorId: string;
  sourceId: string;
  outcome: string;
  participants: string[];
  nextStep: string | null;
  citation: string; // The "smoking gun" quote from the source
  linearIds: string[]; // Associated Linear issues if linked
  isHidden: boolean;
  createdAt: string;
  updatedAt: string;
}

/**
 * DecisionStore manages decisions per project.
 */
export interface DecisionStore {
  listDecisions(projectId: string): Promise<Decision[]>;
  saveDecision(projectId: string, decision: Decision): Promise<void>;
  deleteDecision(projectId: string, decisionId: string): Promise<void>;
  hideDecision(projectId: string, decisionId: string): Promise<void>;
}
