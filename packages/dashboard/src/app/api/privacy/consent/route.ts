import { NextRequest, NextResponse } from 'next/server';
import {
  getProjectConsent,
  revokeProjectConsent,
  setProjectConsent,
} from '@/lib/privacy/consent-store';
import { withAuth } from '@/lib/auth-middleware';

function badRequest(message: string): NextResponse {
  return NextResponse.json({ error: message }, { status: 400 });
}

async function getHandler(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const projectId = searchParams.get('projectId');

  if (!projectId) {
    return badRequest('projectId is required.');
  }

  const consent = await getProjectConsent(projectId);

  return NextResponse.json({
    projectId,
    remoteInferenceEnabled: consent?.remoteInferenceEnabled === true,
    updatedAt: consent?.updatedAt ?? null,
  });
}

async function putHandler(request: NextRequest) {
  const body = await request.json().catch(() => null);
  const projectId = body?.projectId;
  const remoteInferenceEnabled = body?.remoteInferenceEnabled;

  if (typeof projectId !== 'string' || !projectId.trim()) {
    return badRequest('projectId is required.');
  }

  if (typeof remoteInferenceEnabled !== 'boolean') {
    return badRequest('remoteInferenceEnabled must be a boolean.');
  }

  const consent = await setProjectConsent(projectId, remoteInferenceEnabled);
  return NextResponse.json({ consent });
}

async function deleteHandler(request: NextRequest) {
  const body = await request.json().catch(() => null);
  const projectId = body?.projectId;

  if (typeof projectId !== 'string' || !projectId.trim()) {
    return badRequest('projectId is required.');
  }

  const consent = await revokeProjectConsent(projectId);
  return NextResponse.json({ consent });
}

export const GET = withAuth(getHandler);
export const PUT = withAuth(putHandler);
export const DELETE = withAuth(deleteHandler);
