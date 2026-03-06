export interface PipelineStage {
  name: string;
  status: 'pending' | 'active' | 'completed' | 'failed';
  timestamp?: number;
  duration?: number;
  agent?: string;
}

export interface PipelineItem {
  taskId: string;
  projectId: string;
  stages: PipelineStage[];
  totalDuration?: number;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
}

export function filterPipelines(pipelines: PipelineItem[], taskId?: string | null): PipelineItem[] {
  return taskId ? pipelines.filter(p => p.taskId === taskId) : pipelines.slice(0, 20);
}
