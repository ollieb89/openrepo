import { NextRequest } from 'next/server';
import { getActiveProjectId } from '@/lib/openclaw';
import { spawnSync } from 'child_process';
import path from 'path';

const OPENCLAW_ROOT = process.env.OPENCLAW_ROOT || '/home/ollie/.openclaw';

export async function POST(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const projectId = request.nextUrl.searchParams.get('project') || await getActiveProjectId();
    const taskId = params.id;
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
      return Response.json({ error: 'Failed to resume task' }, { status: 500 });
    }

    return Response.json({ ok: true });
  } catch (error) {
    console.error('Error resuming task:', error);
    return Response.json({ error: 'Failed to resume task' }, { status: 500 });
  }
}
