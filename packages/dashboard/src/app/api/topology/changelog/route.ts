import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs/promises';
import path from 'path';
import os from 'os';
import { getActiveProjectId } from '@/lib/openclaw';
import { withAuth } from '@/lib/auth-middleware';
import type { ChangelogApiResponse, ChangelogEntry } from '@/lib/types/topology';

const OPENCLAW_ROOT = process.env.OPENCLAW_ROOT || path.join(os.homedir(), '.openclaw');

async function handler(request: NextRequest): Promise<NextResponse> {
  try {
    const { searchParams } = new URL(request.url);
    const projectId = searchParams.get('project') || await getActiveProjectId();

    const topologyDir = path.join(
      OPENCLAW_ROOT,
      'workspace',
      '.openclaw',
      projectId,
      'topology'
    );

    let changelog: ChangelogEntry[] = [];

    try {
      const raw = await fs.readFile(path.join(topologyDir, 'changelog.json'), 'utf-8');
      changelog = JSON.parse(raw) as ChangelogEntry[];
    } catch {
      // No changelog file — return empty array (no corrections made yet)
    }

    const response: ChangelogApiResponse = { changelog, projectId };
    return NextResponse.json(response);
  } catch (error) {
    console.error('Error loading topology changelog:', error);
    return NextResponse.json({ error: 'Failed to load topology changelog' }, { status: 500 });
  }
}

export const GET = withAuth(handler);
