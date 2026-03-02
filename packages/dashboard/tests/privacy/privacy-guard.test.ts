import { beforeEach, describe, expect, it } from 'vitest';
import {
  addPrivacyAuditEvent,
  listPrivacyAuditEvents,
  resetPrivacyAuditLogForTests,
} from '../../src/lib/privacy/audit-log';
import { createPrivacyGuard } from '../../src/lib/privacy/guard';
import { runRuntimeInference } from '../../src/lib/privacy/runtime-inference';
import { resetConsentStoreForTests, setProjectConsent } from '../../src/lib/privacy/consent-store';

describe('privacy guard', () => {
  beforeEach(() => {
    resetConsentStoreForTests();
    resetPrivacyAuditLogForTests();
    delete process.env.PRIVACY_LOCAL_CONFIDENCE_THRESHOLD;
  });

  it('defaults to local execution without consent', async () => {
    const guard = createPrivacyGuard();
    let localCalled = 0;

    const output = await guard.runInference({
      projectId: 'project-alpha',
      localConfidence: 0.2,
      localExecute: async () => {
        localCalled += 1;
        return 'local-result';
      },
      remotePayload: { input: 'test' },
      remoteConfig: { endpoint: 'https://remote.example.com/infer' },
    });

    expect(output.decision.mode).toBe('local');
    expect(output.decision.hasConsent).toBe(false);
    expect(output.decision.reason).toContain('consent');
    expect(output.result).toBe('local-result');
    expect(localCalled).toBe(1);
  });

  it('keeps high-confidence execution local even with consent', async () => {
    await setProjectConsent('project-alpha', true);
    const guard = createPrivacyGuard({
      transportFactory: () => ({
        invoke: async () => 'remote-result',
      }),
    });

    const output = await guard.runInference({
      projectId: 'project-alpha',
      localConfidence: 0.95,
      localExecute: async () => 'local-result',
      remotePayload: { input: 'test' },
      remoteConfig: { endpoint: 'https://remote.example.com/infer' },
    });

    expect(output.decision.mode).toBe('local');
    expect(output.result).toBe('local-result');
  });

  it('allows remote only for low-confidence requests with explicit project consent', async () => {
    await setProjectConsent('project-alpha', true);

    const guard = createPrivacyGuard({
      transportFactory: () => ({
        invoke: async () => ({ answer: 'remote-result' }),
      }),
    });

    const output = await guard.runInference({
      projectId: 'project-alpha',
      localConfidence: 0.1,
      localExecute: async () => 'local-result',
      remotePayload: { input: 'test' },
      remoteConfig: { endpoint: 'https://remote.example.com/infer' },
      mapRemoteResult: (result) => (result as { answer: string }).answer,
    });

    expect(output.decision.mode).toBe('remote');
    expect(output.decision.hasConsent).toBe(true);
    expect(output.result).toBe('remote-result');
  });

  it('keeps consent scoped to each project', async () => {
    await setProjectConsent('project-alpha', true);

    const guard = createPrivacyGuard({
      transportFactory: () => ({
        invoke: async () => 'remote-result',
      }),
    });

    const allowed = await guard.decide({
      projectId: 'project-alpha',
      localConfidence: 0.05,
    });

    const blocked = await guard.decide({
      projectId: 'project-beta',
      localConfidence: 0.05,
    });

    expect(allowed.mode).toBe('remote');
    expect(blocked.mode).toBe('local');
    expect(blocked.reason).toContain('consent');
  });
});

describe('privacy audit log', () => {
  beforeEach(() => {
    resetPrivacyAuditLogForTests();
  });

  it('stores and filters events by project, mode, connector, reason, and range', () => {
    addPrivacyAuditEvent({
      projectId: 'project-alpha',
      mode: 'remote',
      reason: 'Low confidence with consent',
      connector: 'inference',
      createdAt: '2026-02-24T00:00:00.000Z',
    });
    addPrivacyAuditEvent({
      projectId: 'project-alpha',
      mode: 'local',
      reason: 'Consent missing',
      connector: 'embedding',
      createdAt: '2026-02-24T01:00:00.000Z',
    });
    addPrivacyAuditEvent({
      projectId: 'project-beta',
      mode: 'remote',
      reason: 'Low confidence with consent',
      connector: 'inference',
      createdAt: '2026-02-24T02:00:00.000Z',
    });

    expect(listPrivacyAuditEvents({ projectId: 'project-alpha' })).toHaveLength(2);
    expect(listPrivacyAuditEvents({ mode: 'remote' })).toHaveLength(2);
    expect(listPrivacyAuditEvents({ connector: 'embedding' })).toHaveLength(1);
    expect(listPrivacyAuditEvents({ reason: 'consent missing' })).toHaveLength(1);
    expect(
      listPrivacyAuditEvents({
        from: '2026-02-24T00:30:00.000Z',
        to: '2026-02-24T01:30:00.000Z',
      })
    ).toHaveLength(1);
  });
});

describe('runtime inference guard wiring', () => {
  it('uses guard output for denied remote scenarios and preserves deny-path messaging', async () => {
    const guardInvocations: unknown[] = [];
    let loggedRemote = 0;

    const result = await runRuntimeInference(
      {
        projectId: 'project-alpha',
        prompt: 'summarize blockers',
        localConfidence: 0.1,
      },
      {
        guard: {
          runInference: async (input) => {
            guardInvocations.push(input);
            const localOutput = await input.localExecute();
            return {
              decision: {
                mode: 'local',
                projectId: 'project-alpha',
                reason: 'Project consent missing; remote execution is blocked.',
                localConfidence: 0.1,
                threshold: 0.6,
                hasConsent: false,
              },
              result: localOutput,
            };
          },
        },
        logRemoteUsage: async () => {
          loggedRemote += 1;
        },
      }
    );

    expect(guardInvocations).toHaveLength(1);
    expect(result.mode).toBe('local');
    expect(result.reason).toContain('consent');
    expect(result.output).toContain('Local-only result');
    expect(result.improvementNote).toContain('Enable consent in Privacy Settings');
    expect(loggedRemote).toBe(0);
  });

  it('uses guard-approved remote scenarios and preserves remote mode metadata for badges/audit', async () => {
    let loggedReason = '';

    const result = await runRuntimeInference(
      {
        projectId: 'project-alpha',
        prompt: 'summarize blockers',
        localConfidence: 0.1,
      },
      {
        guard: {
          runInference: async (input) => {
            expect(input.remoteConfig.endpoint.startsWith('https://')).toBe(true);
            return {
              decision: {
                mode: 'remote',
                projectId: 'project-alpha',
                reason: 'Low confidence and explicit project consent allow remote execution.',
                localConfidence: 0.1,
                threshold: 0.6,
                hasConsent: true,
              },
              result: 'Remote-assisted result',
            };
          },
        },
        logRemoteUsage: async (_projectId, reason) => {
          loggedReason = reason;
        },
      }
    );

    expect(result.mode).toBe('remote');
    expect(result.reason).toContain('explicit project consent');
    expect(result.improvementNote).toBeNull();
    expect(loggedReason).toContain('explicit project consent');
  });
});
