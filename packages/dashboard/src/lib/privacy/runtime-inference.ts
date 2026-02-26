import { getPrivacyGuard } from '@/lib/privacy/guard';
import type { PrivacyDecision, PrivacyExecutionMode } from '@/lib/types/privacy';

const DEFAULT_REMOTE_ENDPOINT =
  process.env.NEXT_PUBLIC_PRIVACY_REMOTE_INFERENCE_ENDPOINT ?? 'https://postman-echo.com/post';

const CONSENT_IMPROVEMENT_NOTE =
  'Remote inference is currently denied for this project. Enable consent in Privacy Settings to improve low-confidence outputs.';

export interface RuntimeInferenceInput {
  projectId: string;
  prompt: string;
  localConfidence: number;
}

export interface RuntimeInferenceResult {
  output: string;
  mode: PrivacyExecutionMode;
  reason: string;
  improvementNote: string | null;
}

type GuardRunInferenceInput = Parameters<ReturnType<typeof getPrivacyGuard>['runInference']>[0];

interface RuntimeInferenceDependencies {
  guard?: Pick<ReturnType<typeof getPrivacyGuard>, 'runInference'>;
  remoteEndpoint?: string;
  logRemoteUsage?: (projectId: string, reason: string) => Promise<void>;
}

function inferLocally(prompt: string): string {
  return `Local-only result: ${prompt.slice(0, 180) || 'No prompt provided.'}`;
}

function inferRemotelyFallback(prompt: string): string {
  return `Remote-assisted result: ${prompt.slice(0, 180) || 'No prompt provided.'}`;
}

function mapRemoteResult(rawResult: unknown, prompt: string): string {
  if (typeof rawResult === 'string') {
    return rawResult;
  }

  if (
    typeof rawResult === 'object' &&
    rawResult !== null &&
    'answer' in rawResult &&
    typeof (rawResult as { answer: unknown }).answer === 'string'
  ) {
    return (rawResult as { answer: string }).answer;
  }

  return inferRemotelyFallback(prompt);
}

function toRuntimeResult(
  decision: PrivacyDecision,
  result: unknown
): RuntimeInferenceResult {
  const isConsentBlocked =
    decision.mode === 'local' &&
    decision.hasConsent === false &&
    decision.localConfidence < decision.threshold;

  return {
    output: typeof result === 'string' ? result : String(result),
    mode: decision.mode,
    reason: decision.reason,
    improvementNote: isConsentBlocked ? CONSENT_IMPROVEMENT_NOTE : null,
  };
}

async function defaultRemoteUsageLogger(projectId: string, reason: string): Promise<void> {
  await fetch('/api/privacy/events', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      projectId,
      mode: 'remote',
      reason,
      connector: 'inference',
    }),
  });
}

export async function runRuntimeInference(
  input: RuntimeInferenceInput,
  dependencies: RuntimeInferenceDependencies = {}
): Promise<RuntimeInferenceResult> {
  const guard = dependencies.guard ?? getPrivacyGuard();
  const logRemoteUsage = dependencies.logRemoteUsage ?? defaultRemoteUsageLogger;
  const remoteEndpoint = dependencies.remoteEndpoint ?? DEFAULT_REMOTE_ENDPOINT;

  const guardInput: GuardRunInferenceInput = {
    projectId: input.projectId,
    localConfidence: input.localConfidence,
    localExecute: async () => inferLocally(input.prompt),
    remotePayload: { prompt: input.prompt },
    remoteConfig: { endpoint: remoteEndpoint },
    mapRemoteResult: (rawResult: unknown) => mapRemoteResult(rawResult, input.prompt),
  };

  const output = await guard.runInference(guardInput);
  const runtimeResult = toRuntimeResult(output.decision, output.result);

  if (output.decision.mode === 'remote') {
    await logRemoteUsage(input.projectId, output.decision.reason);
  }

  return runtimeResult;
}
