import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs/promises';
import path from 'path';
import { getActiveProjectId } from '@/lib/openclaw';
import { withAuth } from '@/lib/auth-middleware';
import type { TopologyApiResponse, TopologyGraph, ProposalSet } from '@/lib/types/topology';

const OPENCLAW_ROOT = process.env.OPENCLAW_ROOT || '/home/ollie/.openclaw';

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

    let approved: TopologyGraph | null = null;
    let proposals: ProposalSet | null = null;

    try {
      const raw = await fs.readFile(path.join(topologyDir, 'current.json'), 'utf-8');
      approved = JSON.parse(raw) as TopologyGraph;
    } catch {
      // No current topology file — return null (project has no approved topology yet)
    }

    try {
      const raw = await fs.readFile(path.join(topologyDir, 'pending-proposals.json'), 'utf-8');
      proposals = JSON.parse(raw) as ProposalSet;
    } catch {
      // No pending proposals file — return null
    }

    const response: TopologyApiResponse = { approved, proposals, projectId };
    return NextResponse.json(response);
  } catch (error) {
    console.error('Error loading topology:', error);
    return NextResponse.json({ error: 'Failed to load topology' }, { status: 500 });
  }
}

export const GET = withAuth(handler);
