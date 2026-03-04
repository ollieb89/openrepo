import { NextResponse } from 'next/server';
import { getWorkspaceHealth, initializeWorkspace } from '@/lib/filesystem-utils';
import { withAuth } from '@/lib/auth-middleware';
import path from 'path';
import os from 'os';
import fs from 'fs/promises';

const OPENCLAW_ROOT = process.env.OPENCLAW_ROOT || path.join(os.homedir(), '.openclaw');

async function getHandler() {
  try {
    const health = await getWorkspaceHealth(OPENCLAW_ROOT);
    
    let projectCount = 0;
    let agentCount = 0;

    if (health.checks.root) {
      try {
        if (health.checks.projects) {
          const projectsDir = path.join(OPENCLAW_ROOT, 'projects');
          const entries = await fs.readdir(projectsDir, { withFileTypes: true });
          projectCount = entries.filter(e => e.isDirectory() && !e.name.startsWith('_')).length;
        }
      } catch {
        // Ignore errors in stats collection
      }
    }

    const response = {
      workspace_root: OPENCLAW_ROOT,
      healthy: health.healthy,
      checks: health.checks,
      stats: {
        projects: projectCount,
        agents: agentCount,
      },
      timestamp: new Date().toISOString(),
    };

    return NextResponse.json(response, {
      status: health.healthy ? 200 : 503,
    });
  } catch (error) {
    console.error('[Health Check] Error:', error);
    return NextResponse.json(
      {
        workspace_root: OPENCLAW_ROOT,
        healthy: false,
        error: 'Failed to perform health check',
        timestamp: new Date().toISOString(),
      },
      { status: 503 }
    );
  }
}

async function postHandler() {
  try {
    const result = await initializeWorkspace(OPENCLAW_ROOT);
    
    if (result.success) {
      return NextResponse.json({
        success: true,
        message: 'Workspace initialized successfully',
        workspace_root: OPENCLAW_ROOT,
      });
    } else {
      return NextResponse.json(
        {
          success: false,
          error: result.error?.message || 'Unknown error',
          code: result.error?.code,
          hint: getHintForError(result.error?.code || ''),
        },
        { status: 500 }
      );
    }
  } catch (error) {
    console.error('[Health Check] Initialization error:', error);
    return NextResponse.json(
      {
        success: false,
        error: 'Failed to initialize workspace',
      },
      { status: 500 }
    );
  }
}

function getHintForError(code: string): string {
  switch (code) {
    case 'EACCES':
      return 'Check that you have write permissions to the parent directory. You may need to run: chmod +w on the parent directory.';
    case 'ENOSPC':
      return 'Free up disk space and try again.';
    case 'EROFS':
      return 'The filesystem is mounted as read-only. Check mount options.';
    default:
      return 'Check filesystem permissions and disk space.';
  }
}

export const GET = withAuth(getHandler);
export const POST = withAuth(postHandler);
