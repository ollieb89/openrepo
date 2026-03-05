import { NextRequest, NextResponse } from 'next/server';
import { getTaskState, getActiveProjectId } from '@/lib/openclaw';
import { withAuth } from '@/lib/auth-middleware';

interface PipelineStage {
  name: string;
  status: 'pending' | 'active' | 'completed' | 'failed';
  timestamp?: number;
  duration?: number;
  agent?: string;
}

interface PipelineItem {
  taskId: string;
  projectId: string;
  stages: PipelineStage[];
  totalDuration?: number;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
}

export function filterPipelines(pipelines: PipelineItem[], taskId?: string | null): PipelineItem[] {
  return taskId ? pipelines.filter(p => p.taskId === taskId) : pipelines.slice(0, 20);
}

async function handler(request: NextRequest): Promise<NextResponse> {
  try {
    const { searchParams } = new URL(request.url);
    const projectId = searchParams.get('project') || await getActiveProjectId();
    
    const tasks = await getTaskState(projectId);
    
    const pipelines: PipelineItem[] = tasks.map(task => {
      const metadata = task.metadata as Record<string, any> || {};
      
      // Build pipeline stages based on task state
      const stages: PipelineStage[] = [
        {
          name: 'L1 Dispatch',
          status: 'completed', // Always completed if task exists
          timestamp: task.created_at,
          agent: 'main',
        },
        {
          name: 'L2 Routing',
          status: metadata.routed_at ? 'completed' : 
                  task.status === 'pending' ? 'pending' : 'completed',
          timestamp: metadata.routed_at,
          agent: metadata.l2_agent || 'clawdia_prime',
        },
        {
          name: 'L3 Spawn',
          status: metadata.container_started_at ? 'completed' :
                  task.status === 'pending' ? 'pending' : 'active',
          timestamp: metadata.container_started_at,
          duration: metadata.container_started_at && metadata.routed_at 
            ? metadata.container_started_at - metadata.routed_at 
            : undefined,
          agent: metadata.l3_agent || 'l3_specialist',
        },
        {
          name: 'L3 Execution',
          status: task.status === 'in_progress' || task.status === 'starting' ? 'active' :
                  task.status === 'completed' ? 'completed' :
                  task.status === 'failed' || task.status === 'rejected' ? 'failed' :
                  'pending',
          timestamp: metadata.container_started_at,
          duration: metadata.completed_at && metadata.container_started_at
            ? metadata.completed_at - metadata.container_started_at
            : undefined,
          agent: metadata.l3_agent || 'l3_specialist',
        },
        {
          name: 'L2 Review',
          status: task.status === 'testing' ? 'active' :
                  task.status === 'completed' || task.status === 'failed' ? 'completed' :
                  'pending',
          timestamp: metadata.review_started_at,
          agent: metadata.l2_agent || 'clawdia_prime',
        },
        {
          name: 'Merge',
          status: task.status === 'completed' ? 'completed' : 'pending',
          timestamp: metadata.completed_at,
          agent: metadata.l2_agent || 'clawdia_prime',
        },
      ];
      
      // Calculate total duration
      const totalDuration = metadata.completed_at && task.created_at
        ? metadata.completed_at - task.created_at
        : undefined;
      
      return {
        taskId: task.id,
        projectId,
        stages,
        totalDuration,
        status: task.status as any,
      };
    });
    
    // Sort by most recent activity
    pipelines.sort((a, b) => {
      const aTime = a.stages.find(s => s.timestamp)?.timestamp || 0;
      const bTime = b.stages.find(s => s.timestamp)?.timestamp || 0;
      return bTime - aTime;
    });
    
    return NextResponse.json({
      projectId,
      pipelines: filterPipelines(pipelines, searchParams.get('taskId')),
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error('Error loading pipeline timeline:', error);
    return NextResponse.json(
      { error: 'Failed to load pipeline timeline' },
      { status: 500 }
    );
  }
}

export const GET = withAuth(handler);
