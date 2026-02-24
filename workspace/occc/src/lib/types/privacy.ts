export type PrivacyExecutionMode = 'local' | 'remote';
export type PersistenceRawContentMode = 'reject' | 'strip';
export type PersistedEntityType = string;

export interface PrivacyPolicy {
  localConfidenceThreshold: number;
}

export interface ProjectConsent {
  projectId: string;
  remoteInferenceEnabled: boolean;
  updatedAt: string;
}

export interface ConsentStore {
  getConsent(projectId: string): Promise<ProjectConsent | null>;
  setConsent(projectId: string, remoteInferenceEnabled: boolean): Promise<ProjectConsent>;
  revokeConsent(projectId: string): Promise<ProjectConsent>;
}

export interface PrivacyDecision {
  mode: PrivacyExecutionMode;
  projectId: string;
  reason: string;
  localConfidence: number;
  threshold: number;
  hasConsent: boolean;
}

export interface GuardDecisionInput {
  projectId: string;
  localConfidence: number;
}

export interface RemoteTransportConfig {
  endpoint: string;
  timeoutMs?: number;
  tls?: {
    rejectUnauthorized?: boolean;
  };
}

export interface RemoteTransport {
  invoke(payload: unknown): Promise<unknown>;
}

export interface ProvenanceMetadata {
  sourceLink: string;
  timestamp: string;
  connectorLabel: string;
}

export interface PersistedMetadataRecord {
  sourceId: string;
  threadId?: string;
  timestamp: string;
  connector: string;
  entityType: PersistedEntityType;
  provenance: ProvenanceMetadata;
}

export interface PersistedMetadataInput {
  sourceId?: string;
  threadId?: string;
  timestamp?: string;
  connector?: string;
  entityType?: PersistedEntityType;
  provenance?: Partial<ProvenanceMetadata>;
  [key: string]: unknown;
}
