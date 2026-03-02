import fs from 'fs/promises';
import { existsSync } from 'fs';
import path from 'path';
import { execFile } from 'child_process';
import { promisify } from 'util';
import { NextRequest, NextResponse } from 'next/server';
import { withAuth } from '@/lib/auth-middleware';

const OPENCLAW_ROOT = process.env.OPENCLAW_ROOT || '/home/ollie/.openclaw';
const ORCHESTRATION_ROOT = path.join(OPENCLAW_ROOT, 'packages', 'orchestration', 'src', 'openclaw');

if (!existsSync(path.join(ORCHESTRATION_ROOT, 'soul_renderer.py'))) {
  console.warn('[suggestions/action] soul_renderer.py not found at expected path — check OPENCLAW_ROOT env var');
}
const MAX_DIFF_LINES = 100;
const FORBIDDEN_PATTERNS: RegExp[] = [
  /cap_drop/i,
  /no-new-privileges/i,
  /LOCK_TIMEOUT/i,
  /shell=/i,
  /exec\s*\(/i,
  /subprocess/i,
  /os\.system/i,
  /`[^`]+`/,        // backtick shell commands
  /\$\([^)]+\)/,    // shell substitution $(...)
];

function validateDiffText(diffText: unknown): { valid: boolean; reason?: string } {
  if (diffText === null || diffText === undefined || diffText === '') {
    return { valid: false, reason: 'diff_text is required and must be a non-empty string' };
  }
  if (typeof diffText !== 'string') {
    return { valid: false, reason: 'diff_text must be a string' };
  }
  const lines = diffText.split('\n');
  if (lines.length > MAX_DIFF_LINES) {
    return { valid: false, reason: `Diff exceeds ${MAX_DIFF_LINES} lines (got ${lines.length})` };
  }
  for (const pattern of FORBIDDEN_PATTERNS) {
    if (pattern.test(diffText)) {
      return { valid: false, reason: `Diff contains forbidden pattern: ${pattern}` };
    }
  }
  return { valid: true };
}

function suggestionsPath(projectId: string): string {
  return path.join(OPENCLAW_ROOT, 'workspace', '.openclaw', projectId, 'soul-suggestions.json');
}

function soulOverridePath(projectId: string): string {
  return path.join(OPENCLAW_ROOT, 'projects', projectId, 'soul-override.md');
}

async function rerenderSoul(projectId: string): Promise<void> {
  const execFileAsync = promisify(execFile);
  await execFileAsync('python3', [
    path.join(ORCHESTRATION_ROOT, 'soul_renderer.py'),
    '--project', projectId, '--write', '--force',
  ], { cwd: OPENCLAW_ROOT });
}

interface SuggestionRecord {
  id: string;
  status: string;
  evidence_count: number;
  accepted_at?: number;
  rejected_at?: number;
  rejection_reason?: string | null;
  suppressed_until_count?: number;
}

interface SuggestionsFile {
  version: string;
  last_run: number | null;
  suggestions: SuggestionRecord[];
}

async function handler(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id: suggestionId } = await params;

  let body: {
    action?: string;
    project?: string;
    diff_text?: unknown;
    rejection_reason?: string;
  };

  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  const { action, project } = body;

  if (!action || !project) {
    return NextResponse.json({ error: 'action and project are required' }, { status: 400 });
  }

  // Read soul-suggestions.json
  let suggestionsData: SuggestionsFile;
  try {
    const raw = await fs.readFile(suggestionsPath(project), 'utf-8');
    suggestionsData = JSON.parse(raw);
  } catch (error: unknown) {
    if (error instanceof Error && 'code' in error && (error as NodeJS.ErrnoException).code === 'ENOENT') {
      return NextResponse.json({ error: 'No suggestions found for this project' }, { status: 404 });
    }
    console.error('Error reading soul-suggestions.json:', error);
    return NextResponse.json({ error: 'Failed to read suggestions' }, { status: 500 });
  }

  // Find the suggestion by id
  const suggestionIndex = suggestionsData.suggestions.findIndex(s => s.id === suggestionId);
  if (suggestionIndex === -1) {
    return NextResponse.json({ error: `Suggestion '${suggestionId}' not found` }, { status: 404 });
  }

  const suggestion = suggestionsData.suggestions[suggestionIndex];

  if (action === 'accept') {
    // Approval gate — validateDiffText must pass before any file write
    const validation = validateDiffText(body.diff_text);
    if (!validation.valid) {
      return NextResponse.json({ error: validation.reason }, { status: 422 });
    }

    const diffText = body.diff_text as string;

    // Create soul-override.md directory if missing (Pitfall 5)
    await fs.mkdir(path.dirname(soulOverridePath(project)), { recursive: true });

    // Append to soul-override.md — only called after validateDiffText passes
    await fs.appendFile(
      soulOverridePath(project),
      '\n\n' + diffText.trim() + '\n',
      'utf-8'
    );

    // Re-render SOUL.md via soul_renderer.py
    try {
      await rerenderSoul(project);
    } catch (error) {
      console.error('Error re-rendering SOUL:', error);
      // Don't fail the whole request — the content was already appended
    }

    // Update suggestion status
    suggestionsData.suggestions[suggestionIndex] = {
      ...suggestion,
      status: 'accepted',
      accepted_at: Date.now() / 1000,
    };

    // Write updated JSON back
    await fs.writeFile(suggestionsPath(project), JSON.stringify(suggestionsData, null, 2), 'utf-8');

    return NextResponse.json({ ok: true, message: 'Applied to soul-override.md' });

  } else if (action === 'reject') {
    // Update suggestion status with suppression
    suggestionsData.suggestions[suggestionIndex] = {
      ...suggestion,
      status: 'rejected',
      rejected_at: Date.now() / 1000,
      rejection_reason: body.rejection_reason ?? null,
      suppressed_until_count: suggestion.evidence_count * 2,
    };

    // Write updated JSON back
    await fs.writeFile(suggestionsPath(project), JSON.stringify(suggestionsData, null, 2), 'utf-8');

    // Rejection reason memorization deferred to L2 CLI — dashboard doesn't call memU directly
    return NextResponse.json({ ok: true });

  } else {
    return NextResponse.json({ error: `Unknown action: '${action}'` }, { status: 400 });
  }
}

export const POST = withAuth(handler);
