import fs from 'fs/promises';
import path from 'path';
import { execFile } from 'child_process';
import { promisify } from 'util';
import { NextRequest } from 'next/server';

const OPENCLAW_ROOT = process.env.OPENCLAW_ROOT || '/home/ollie/.openclaw';
const execFileAsync = promisify(execFile);

function suggestionsPath(projectId: string): string {
  return path.join(OPENCLAW_ROOT, 'workspace', '.openclaw', projectId, 'soul-suggestions.json');
}

const EMPTY_STATE = { version: '1.0', last_run: null, suggestions: [] };

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const projectId = searchParams.get('project');

  if (!projectId) {
    return Response.json({ error: 'project query parameter is required' }, { status: 400 });
  }

  try {
    const raw = await fs.readFile(suggestionsPath(projectId), 'utf-8');
    const data = JSON.parse(raw);
    return Response.json(data);
  } catch (error: unknown) {
    if (error instanceof Error && 'code' in error && (error as NodeJS.ErrnoException).code === 'ENOENT') {
      // File not found — return empty state (valid)
      return Response.json(EMPTY_STATE);
    }
    console.error('Error reading soul-suggestions.json:', error);
    return Response.json({ error: 'Failed to read suggestions' }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const projectId = searchParams.get('project');

  if (!projectId) {
    return Response.json({ error: 'project query parameter is required' }, { status: 400 });
  }

  const orchestrationPath = path.join(OPENCLAW_ROOT, 'orchestration', 'suggest.py');

  try {
    await execFileAsync('python3', [orchestrationPath, '--project', projectId], {
      timeout: 60000,
      cwd: OPENCLAW_ROOT,
    });
  } catch (error: unknown) {
    if (error instanceof Error && 'killed' in error && (error as NodeJS.ErrnoException & { killed: boolean }).killed) {
      return Response.json({ error: 'Suggestion analysis timed out' }, { status: 504 });
    }
    const execError = error as { code?: number; stderr?: string };
    if (execError.code !== undefined && execError.code !== 0) {
      return Response.json(
        { error: 'suggest.py exited with error', stderr: execError.stderr ?? '' },
        { status: 500 }
      );
    }
    console.error('Error running suggest.py:', error);
    return Response.json({ error: 'Failed to run suggestion analysis' }, { status: 500 });
  }

  // Read updated suggestions file after subprocess completes
  try {
    const raw = await fs.readFile(suggestionsPath(projectId), 'utf-8');
    const data = JSON.parse(raw);
    return Response.json(data);
  } catch (error: unknown) {
    if (error instanceof Error && 'code' in error && (error as NodeJS.ErrnoException).code === 'ENOENT') {
      return Response.json(EMPTY_STATE);
    }
    console.error('Error reading soul-suggestions.json after run:', error);
    return Response.json({ error: 'Analysis ran but failed to read results' }, { status: 500 });
  }
}
