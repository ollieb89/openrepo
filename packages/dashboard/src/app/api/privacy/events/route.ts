import { NextRequest, NextResponse } from 'next/server';
import {
  addPrivacyAuditEvent,
  listPrivacyAuditEvents,
  type CreatePrivacyAuditEventInput,
  type PrivacyAuditEventFilters,
} from '@/lib/privacy/audit-log';
import { withAuth } from '@/lib/auth-middleware';

function badRequest(message: string): NextResponse {
  return NextResponse.json({ error: message }, { status: 400 });
}

function parseFilters(request: NextRequest): PrivacyAuditEventFilters {
  const { searchParams } = new URL(request.url);
  const filters: PrivacyAuditEventFilters = {};

  const projectId = searchParams.get('projectId');
  const mode = searchParams.get('mode');
  const reason = searchParams.get('reason');
  const connector = searchParams.get('connector');
  const from = searchParams.get('from');
  const to = searchParams.get('to');

  if (projectId) filters.projectId = projectId;
  if (mode === 'local' || mode === 'remote') filters.mode = mode;
  if (reason) filters.reason = reason;
  if (connector) filters.connector = connector;
  if (from) filters.from = from;
  if (to) filters.to = to;

  return filters;
}

async function getHandler(request: NextRequest) {
  const events = listPrivacyAuditEvents(parseFilters(request));
  return NextResponse.json({ events });
}

async function postHandler(request: NextRequest) {
  const body = await request.json().catch(() => null);
  const input = body as CreatePrivacyAuditEventInput | null;

  if (!input || typeof input.projectId !== 'string' || !input.projectId.trim()) {
    return badRequest('projectId is required.');
  }

  if (input.mode !== 'local' && input.mode !== 'remote') {
    return badRequest('mode must be "local" or "remote".');
  }

  if (typeof input.reason !== 'string' || !input.reason.trim()) {
    return badRequest('reason is required.');
  }

  const event = addPrivacyAuditEvent({
    projectId: input.projectId,
    mode: input.mode,
    reason: input.reason,
    connector: input.connector,
    createdAt: input.createdAt,
  });

  return NextResponse.json({ event }, { status: 201 });
}

export const GET = withAuth(getHandler);
export const POST = withAuth(postHandler);
