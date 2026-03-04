import { NextRequest, NextResponse } from 'next/server';
import { getActiveProjectId } from '@/lib/openclaw';
import { withAuth } from '@/lib/auth-middleware';
import { spawnSync } from 'child_process';
import path from 'path';
import os from 'os';

const OPENCLAW_ROOT = process.env.OPENCLAW_ROOT || path.join(os.homedir(), '.openclaw');

async function handler(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: taskId } = await params;
    const projectId = request.nextUrl.searchParams.get('project') || await getActiveProjectId();
    const statePath = path.join(
      OPENCLAW_ROOT,
      'workspace',
      '.openclaw',
      projectId,
      'workspace-state.json'
    );

    const result = spawnSync(
      'uv',
      [
        'run',
        'python',
        '-c',
        `from openclaw.state_engine import JarvisState; js = JarvisState("${statePath}"); js.update_task("${taskId}", "resumed", "Operator resumed via dashboard")`,
      ],
      { cwd: OPENCLAW_ROOT, encoding: 'utf-8' }
    );

    if (result.status !== 0) {
      console.error('Resume failed:', result.stderr);
      return NextResponse.json({ error: 'Failed to resume task' }, { status: 500 });
    }

    return NextResponse.json({ ok: true });
  } catch (error) {
    console.error('Error resuming task:', error);
    return NextResponse.json({ error: 'Failed to resume task' }, { status: 500 });
  }
}

export const POST = withAuth(handler);
