import fs from 'fs/promises';
import path from 'path';
import type { Project, Task, Agent } from './types';
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

export async function getTaskState(projectId: string): Promise<Task[]> {
  const statePath = path.join(
    OPENCLAW_ROOT, 'workspace', '.openclaw', projectId, 'workspace-state.json'
  );

  try {
    const raw = await fs.readFile(statePath, 'utf-8');
    const state = JSON.parse(raw);
    const tasks = state.tasks || {};

    return Object.entries(tasks).map(([id, data]) => ({
      id,
      ...(data as Omit<Task, 'id'>),
    }));
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
