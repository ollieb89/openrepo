import fs from 'fs/promises';
import path from 'path';
import type { Project, Task, Agent } from './types';
import type { TaskWithAutonomy } from './types/autonomy';
import { minimizePersistenceRecord } from './privacy/minimization';
import type { PersistedMetadataInput, PersistedMetadataRecord } from './types/privacy';

const OPENCLAW_ROOT = process.env.OPENCLAW_ROOT || '/home/ollie/.openclaw';

export async function readOpenClawConfig(): Promise<Record<string, unknown>> {
  const raw = await fs.readFile(path.join(OPENCLAW_ROOT, 'openclaw.json'), 'utf-8');
  return JSON.parse(raw);
}

export async function listProjects(): Promise<Project[]> {
  const projectsDir = path.join(OPENCLAW_ROOT, 'projects');
  const entries = await fs.readdir(projectsDir, { withFileTypes: true });
  const projects: Project[] = [];

  for (const entry of entries) {
    if (!entry.isDirectory() || entry.name.startsWith('_')) continue;
    try {
      const raw = await fs.readFile(
        path.join(projectsDir, entry.name, 'project.json'),
        'utf-8'
      );
      projects.push(JSON.parse(raw));
    } catch {
      // Skip projects without valid config
    }
  }

  return projects;
}

export async function getProject(id: string): Promise<Project | null> {
  try {
    const raw = await fs.readFile(
      path.join(OPENCLAW_ROOT, 'projects', id, 'project.json'),
      'utf-8'
    );
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export async function getActiveProjectId(): Promise<string> {
  const config = await readOpenClawConfig();
  return (config.active_project as string) || 'pumplai';
}

/** Map task status to autonomy state for UI display. */
function mapStatusToAutonomyState(
  status: string
): 'planning' | 'executing' | 'blocked' | 'escalating' | 'complete' {
  switch (status) {
    case 'escalating':
      return 'escalating';
    case 'pending':
      return 'planning';
    case 'in_progress':
    case 'starting':
    case 'testing':
      return 'executing';
    case 'completed':
    case 'failed':
    case 'rejected':
      return 'complete';
    default:
      return 'executing';
  }
}

/** Enrich task with autonomy info derived from workspace state. */
function enrichTaskWithAutonomy(task: Task): TaskWithAutonomy {
  const meta = task.metadata || {};
  const autonomyMeta = (meta.autonomy as Record<string, unknown>) || {};
  const status = task.status;
  const lastEntry = task.activity_log?.[task.activity_log.length - 1];

  const autonomy = {
    state: mapStatusToAutonomyState(status),
    confidence_score: (autonomyMeta.confidence_score as number) ?? (status === 'escalating' ? 0.5 : 1),
    selected_tools: (autonomyMeta.selected_tools as string[]) ?? [],
    ...(status === 'escalating' && {
      escalation: {
        reason:
          (autonomyMeta.escalation_reason as string) ?? lastEntry?.entry ?? 'Task escalated',
        confidence: (autonomyMeta.escalation_confidence as number) ?? 0.5,
        timestamp: task.updated_at ?? task.created_at ?? 0,
      },
    }),
  };

  return { ...task, title: task.id, autonomy };
}

export async function getTaskState(
  projectId: string,
  options?: { state?: string }
): Promise<Task[]> {
  const statePath = path.join(
    OPENCLAW_ROOT, 'workspace', '.openclaw', projectId, 'workspace-state.json'
  );

  try {
    const raw = await fs.readFile(statePath, 'utf-8');
    const state = JSON.parse(raw);
    const tasks = state.tasks || {};

    let result = Object.entries(tasks).map(([id, data]) =>
      enrichTaskWithAutonomy({ id, ...(data as Omit<Task, 'id'>) })
    );

    if (options?.state) {
      result = result.filter((t) => t.status === options.state);
    }

    return result;
  } catch {
    return [];
  }
}

export async function getTask(projectId: string, taskId: string): Promise<Task | null> {
  const tasks = await getTaskState(projectId);
  return tasks.find(t => t.id === taskId) || null;
}

export async function listAgents(): Promise<Agent[]> {
  const config = await readOpenClawConfig();
  const agentsList = (config.agents as Record<string, unknown>)?.list;
  if (!Array.isArray(agentsList)) return [];
  return agentsList as Agent[];
}

export async function getSnapshot(projectId: string, taskId: string): Promise<string | null> {
  const snapshotPath = path.join(
    OPENCLAW_ROOT, 'workspace', '.openclaw', projectId, 'snapshots', `${taskId}.diff`
  );

  try {
    return await fs.readFile(snapshotPath, 'utf-8');
  } catch {
    return null;
  }
}

export async function appendMinimizedRecord(
  projectId: string,
  payload: PersistedMetadataInput
): Promise<PersistedMetadataRecord> {
  const minimized = minimizePersistenceRecord(payload, { rawContentMode: 'reject' });
  const logDir = path.join(OPENCLAW_ROOT, 'workspace', '.openclaw', projectId, 'privacy');
  const logPath = path.join(logDir, 'minimized-records.jsonl');

  await fs.mkdir(logDir, { recursive: true });
  await fs.appendFile(logPath, `${JSON.stringify(minimized)}\n`, 'utf-8');

  return minimized;
}
