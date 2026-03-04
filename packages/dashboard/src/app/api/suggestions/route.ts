import fs from 'fs/promises';
import { existsSync } from 'fs';
import path from 'path';
import os from 'os';
import { execFile } from 'child_process';
import { promisify } from 'util';
import { NextRequest, NextResponse } from 'next/server';
import { withAuth } from '@/lib/auth-middleware';

const OPENCLAW_ROOT = process.env.OPENCLAW_ROOT || path.join(os.homedir(), '.openclaw');
const ORCHESTRATION_ROOT = path.join(OPENCLAW_ROOT, 'packages', 'orchestration', 'src', 'openclaw');

if (!existsSync(path.join(ORCHESTRATION_ROOT, 'cli', 'suggest.py'))) {
  console.warn('[suggestions] suggest.py not found at expected path — check OPENCLAW_ROOT env var');
}

const execFileAsync = promisify(execFile);

function suggestionsPath(projectId: string): string {
  return path.join(OPENCLAW_ROOT, 'workspace', '.openclaw', projectId, 'soul-suggestions.json');
}

const EMPTY_STATE = { version: '1.0', last_run: null, suggestions: [] };

async function getHandler(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const projectId = searchParams.get('project');

  if (!projectId) {
    return NextResponse.json({ error: 'project query parameter is required' }, { status: 400 });
  }

  try {
    const raw = await fs.readFile(suggestionsPath(projectId), 'utf-8');
    const data = JSON.parse(raw);
    return NextResponse.json(data);
  } catch (error: unknown) {
    if (error instanceof Error && 'code' in error && (error as NodeJS.ErrnoException).code === 'ENOENT') {
      // File not found — return empty state (valid)
      return NextResponse.json(EMPTY_STATE);
    }
    console.error('Error reading soul-suggestions.json:', error);
    return NextResponse.json({ error: 'Failed to read suggestions' }, { status: 500 });
  }
}

async function postHandler(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const projectId = searchParams.get('project');

  if (!projectId) {
    return NextResponse.json({ error: 'project query parameter is required' }, { status: 400 });
  }

  const orchestrationPath = path.join(ORCHESTRATION_ROOT, 'cli', 'suggest.py');

  try {
    await execFileAsync('python3', [orchestrationPath, '--project', projectId], {
      timeout: 60000,
      cwd: OPENCLAW_ROOT,
    });
  } catch (error: unknown) {
    if (error instanceof Error && 'killed' in error && (error as NodeJS.ErrnoException & { killed: boolean }).killed) {
      return NextResponse.json({ error: 'Suggestion analysis timed out' }, { status: 504 });
    }
    const execError = error as { code?: number; stderr?: string };
    if (execError.code !== undefined && execError.code !== 0) {
      return NextResponse.json(
        { error: 'suggest.py exited with error', stderr: execError.stderr ?? '' },
        { status: 500 }
      );
    }
    console.error('Error running suggest.py:', error);
    return NextResponse.json({ error: 'Failed to run suggestion analysis' }, { status: 500 });
  }

  // Read updated suggestions file after subprocess completes
  try {
    const raw = await fs.readFile(suggestionsPath(projectId), 'utf-8');
    const data = JSON.parse(raw);
    return NextResponse.json(data);
  } catch (error: unknown) {
    if (error instanceof Error && 'code' in error && (error as NodeJS.ErrnoException).code === 'ENOENT') {
      return NextResponse.json(EMPTY_STATE);
    }
    console.error('Error reading soul-suggestions.json after run:', error);
    return NextResponse.json({ error: 'Analysis ran but failed to read results' }, { status: 500 });
  }
}

export const GET = withAuth(getHandler);
export const POST = withAuth(postHandler);
