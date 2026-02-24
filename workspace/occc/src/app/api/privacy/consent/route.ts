import { NextRequest } from 'next/server';
import {
  getProjectConsent,
  revokeProjectConsent,
  setProjectConsent,
} from '@/lib/privacy/consent-store';

function badRequest(message: string): Response {
  return Response.json({ error: message }, { status: 400 });
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const projectId = searchParams.get('projectId');

  if (!projectId) {
    return badRequest('projectId is required.');
  }

  const consent = await getProjectConsent(projectId);

  return Response.json({
    projectId,
    remoteInferenceEnabled: consent?.remoteInferenceEnabled === true,
    updatedAt: consent?.updatedAt ?? null,
  });
}

export async function PUT(request: NextRequest) {
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
  return Response.json({ consent });
}

export async function DELETE(request: NextRequest) {
  const body = await request.json().catch(() => null);
  const projectId = body?.projectId;

  if (typeof projectId !== 'string' || !projectId.trim()) {
    return badRequest('projectId is required.');
  }

  const consent = await revokeProjectConsent(projectId);
  return Response.json({ consent });
}
