import type { ConsentStore, ProjectConsent } from '@/lib/types/privacy';

const consentByProject = new Map<string, ProjectConsent>();

function nowIso(): string {
  return new Date().toISOString();
}

function buildConsent(projectId: string, remoteInferenceEnabled: boolean): ProjectConsent {
  return {
    projectId,
    remoteInferenceEnabled,
    updatedAt: nowIso(),
  };
}

export function createConsentStore(): ConsentStore {
  return {
    async getConsent(projectId: string): Promise<ProjectConsent | null> {
      return consentByProject.get(projectId) ?? null;
    },

    async setConsent(projectId: string, remoteInferenceEnabled: boolean): Promise<ProjectConsent> {
      const consent = buildConsent(projectId, remoteInferenceEnabled);
      consentByProject.set(projectId, consent);
      return consent;
    },

    async revokeConsent(projectId: string): Promise<ProjectConsent> {
      const consent = buildConsent(projectId, false);
      consentByProject.set(projectId, consent);
      return consent;
    },
  };
}

const defaultConsentStore = createConsentStore();

export async function getProjectConsent(projectId: string): Promise<ProjectConsent | null> {
  return defaultConsentStore.getConsent(projectId);
}

export async function setProjectConsent(
  projectId: string,
  remoteInferenceEnabled: boolean
): Promise<ProjectConsent> {
  return defaultConsentStore.setConsent(projectId, remoteInferenceEnabled);
}

export async function revokeProjectConsent(projectId: string): Promise<ProjectConsent> {
  return defaultConsentStore.revokeConsent(projectId);
}

export function getDefaultConsentStore(): ConsentStore {
  return defaultConsentStore;
}

export function resetConsentStoreForTests(): void {
  consentByProject.clear();
}
