import type { PrivacyExecutionMode } from '@/lib/types/privacy';

export interface PrivacyAuditEvent {
  id: string;
  projectId: string;
  mode: PrivacyExecutionMode;
  reason: string;
  connector: string;
  createdAt: string;
}

export interface CreatePrivacyAuditEventInput {
  projectId: string;
  mode: PrivacyExecutionMode;
  reason: string;
  connector?: string;
  createdAt?: string;
}

export interface PrivacyAuditEventFilters {
  projectId?: string;
  mode?: PrivacyExecutionMode;
  reason?: string;
  connector?: string;
  from?: string;
  to?: string;
}

const auditEvents: PrivacyAuditEvent[] = [];

function makeEventId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function normalize(value: string): string {
  return value.trim().toLowerCase();
}

function matches(event: PrivacyAuditEvent, filters: PrivacyAuditEventFilters): boolean {
  if (filters.projectId && event.projectId !== filters.projectId) {
    return false;
  }

  if (filters.mode && event.mode !== filters.mode) {
    return false;
  }

  if (filters.reason && !normalize(event.reason).includes(normalize(filters.reason))) {
    return false;
  }

  if (filters.connector && normalize(event.connector) !== normalize(filters.connector)) {
    return false;
  }

  if (filters.from && event.createdAt < filters.from) {
    return false;
  }

  if (filters.to && event.createdAt > filters.to) {
    return false;
  }

  return true;
}

export function addPrivacyAuditEvent(input: CreatePrivacyAuditEventInput): PrivacyAuditEvent {
  const event: PrivacyAuditEvent = {
    id: makeEventId(),
    projectId: input.projectId,
    mode: input.mode,
    reason: input.reason,
    connector: input.connector?.trim() || 'inference',
    createdAt: input.createdAt ?? new Date().toISOString(),
  };

  auditEvents.push(event);
  return event;
}

export function listPrivacyAuditEvents(filters: PrivacyAuditEventFilters = {}): PrivacyAuditEvent[] {
  return auditEvents
    .filter(event => matches(event, filters))
    .sort((a, b) => b.createdAt.localeCompare(a.createdAt));
}

export function resetPrivacyAuditLogForTests(): void {
  auditEvents.length = 0;
}
