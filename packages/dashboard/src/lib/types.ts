import type { PersistedMetadataRecord } from '@/lib/types/privacy';

export interface Project {
  id: string;
  name: string;
  agent_display_name: string;
  workspace: string;
  tech_stack: {
    frontend?: string;
    backend?: string;
    infra?: string;
  };
  agents: {
    l2_pm: string;
    l3_executor: string;
  };
  l3_overrides?: {
    mem_limit: string;
    cpu_quota: number;
    runtimes: string[];
    max_concurrent?: number;
  };
}

export interface TaskActivityEntry {
  timestamp: number;
  status: string;
  entry: string;
}

export type TaskStatus = 'pending' | 'in_progress' | 'starting' | 'testing' | 'completed' | 'failed' | 'rejected' | 'escalating';

export interface Task {
  id: string;
  status: TaskStatus;
  skill_hint: string;
  activity_log: TaskActivityEntry[];
  created_at: number;
  updated_at: number;
  metadata: Record<string, unknown>;
}

export interface Agent {
  id: string;
  name: string;
  level: number;
  reports_to: string | null;
  project?: string;
  sandbox?: { mode: string };
}

export interface MetricsResponse {
  completionDurations: { id: string; durationS: number }[];
  lifecycle: { pending: number; active: number; completed: number; failed: number };
  poolUtilization: number;
  poolMax: number;
  poolActive: number;
  projectId: string;
  autonomy: {
    avgConfidence: number;
    activeContexts: number;
  };
  memory: {
    healthy: boolean;
    latencyMs?: number;
  };
  todayTokens: number;
  todayCostUsd: number;
  usageLogPresent: boolean;
}

export interface Container {
  id: string;
  name: string;
  status: string;
  image: string;
  created: number;
  labels: Record<string, string>;
}

export interface PersistedTaskRecord extends Omit<Task, 'metadata'> {
  metadata: PersistedMetadataRecord;
}
