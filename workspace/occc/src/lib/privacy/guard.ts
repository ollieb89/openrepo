import {
  getDefaultConsentStore,
} from '@/lib/privacy/consent-store';
import { getPrivacyPolicy } from '@/lib/privacy/policy';
import { createRemoteTransport } from '@/lib/privacy/transport';
import type {
  ConsentStore,
  GuardDecisionInput,
  PrivacyDecision,
  RemoteTransport,
  RemoteTransportConfig,
} from '@/lib/types/privacy';

interface PrivacyGuardOptions {
  consentStore?: ConsentStore;
  transportFactory?: (config: RemoteTransportConfig) => RemoteTransport;
}

interface GuardedExecutionInput<TLocal, TRemote = unknown> {
  projectId: string;
  localConfidence: number;
  localExecute: () => Promise<TLocal>;
  remotePayload: unknown;
  remoteConfig: RemoteTransportConfig;
  mapRemoteResult?: (result: unknown) => TRemote;
}

interface GuardedExecutionResult<TLocal, TRemote = unknown> {
  decision: PrivacyDecision;
  result: TLocal | TRemote;
}

function buildDecision(
  input: GuardDecisionInput,
  hasConsent: boolean,
  threshold: number
): PrivacyDecision {
  if (input.localConfidence >= threshold) {
    return {
      mode: 'local',
      projectId: input.projectId,
      reason: 'Local confidence meets threshold; keeping execution local.',
      localConfidence: input.localConfidence,
      threshold,
      hasConsent,
    };
  }

  if (!hasConsent) {
    return {
      mode: 'local',
      projectId: input.projectId,
      reason: 'Project consent missing; remote execution is blocked.',
      localConfidence: input.localConfidence,
      threshold,
      hasConsent,
    };
  }

  return {
    mode: 'remote',
    projectId: input.projectId,
    reason: 'Low confidence and explicit project consent allow remote execution.',
    localConfidence: input.localConfidence,
    threshold,
    hasConsent,
  };
}

export function createPrivacyGuard(options: PrivacyGuardOptions = {}) {
  const consentStore = options.consentStore ?? getDefaultConsentStore();
  const transportFactory = options.transportFactory ?? createRemoteTransport;

  async function decide(input: GuardDecisionInput): Promise<PrivacyDecision> {
    const policy = getPrivacyPolicy();
    const consent = await consentStore.getConsent(input.projectId);
    const hasConsent = consent?.remoteInferenceEnabled === true;
    return buildDecision(input, hasConsent, policy.localConfidenceThreshold);
  }

  async function runGuardedExecution<TLocal, TRemote = unknown>(
    input: GuardedExecutionInput<TLocal, TRemote>
  ): Promise<GuardedExecutionResult<TLocal, TRemote>> {
    const decision = await decide({
      projectId: input.projectId,
      localConfidence: input.localConfidence,
    });

    if (decision.mode === 'local') {
      return {
        decision,
        result: await input.localExecute(),
      };
    }

    const transport = transportFactory(input.remoteConfig);
    const rawRemoteResult = await transport.invoke(input.remotePayload);

    return {
      decision,
      result: input.mapRemoteResult
        ? input.mapRemoteResult(rawRemoteResult)
        : (rawRemoteResult as TRemote),
    };
  }

  // Single entry point that must gate all local/remote execution decisions.
  async function runInference<TLocal, TRemote = unknown>(
    input: GuardedExecutionInput<TLocal, TRemote>
  ): Promise<GuardedExecutionResult<TLocal, TRemote>> {
    return runGuardedExecution(input);
  }

  // Embeddings follow the same gateway to keep remote routing non-bypassable.
  async function runEmbedding<TLocal, TRemote = unknown>(
    input: GuardedExecutionInput<TLocal, TRemote>
  ): Promise<GuardedExecutionResult<TLocal, TRemote>> {
    return runGuardedExecution(input);
  }

  return {
    decide,
    runInference,
    runEmbedding,
  };
}

const defaultPrivacyGuard = createPrivacyGuard();

export function getPrivacyGuard() {
  return defaultPrivacyGuard;
}
