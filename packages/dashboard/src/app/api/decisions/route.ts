import { NextRequest, NextResponse } from 'next/server';
import { loadDecisions } from '@/lib/sync/storage';
import { withAuth } from '@/lib/auth-middleware';
import path from 'path';
import fs from 'fs';

const GET_RECORDS_ROOT = () => {
  const root = process.env.OPENCLAW_ROOT || '/home/ollie/.openclaw';
  return path.join(root, 'workspace', '.openclaw', 'records', 'decisions');
};

async function handler(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const projectId = searchParams.get('projectId');

  try {
    let allDecisions: any[] = [];

    if (projectId) {
      allDecisions = await loadDecisions(projectId);
    } else {
      // If no projectId, maybe load from all files in the decisions directory?
      // For now, let's just list all .json files in records/decisions
      const decisionsDir = GET_RECORDS_ROOT();
      if (fs.existsSync(decisionsDir)) {
        const files = fs.readdirSync(decisionsDir).filter(f => f.endsWith('.json'));
        for (const file of files) {
          const content = fs.readFileSync(path.join(decisionsDir, file), 'utf8');
          allDecisions = allDecisions.concat(JSON.parse(content));
        }
      }
    }

    // Filter hidden and sort by date descending
    const filteredDecisions = allDecisions
      .filter(d => !d.isHidden)
      .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());

    return NextResponse.json(filteredDecisions);
  } catch (error) {
    console.error('Failed to fetch decisions:', error);
    return NextResponse.json({ error: 'Failed to fetch decisions' }, { status: 500 });
  }
}

export const GET = withAuth(handler);
