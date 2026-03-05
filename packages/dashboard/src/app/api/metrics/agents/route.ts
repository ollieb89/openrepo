import { NextRequest, NextResponse } from 'next/server';
import { getTaskState, getActiveProjectId, listAgents } from '@/lib/openclaw';
import { withAuth } from '@/lib/auth-middleware';

interface AgentMetrics {
  agent_id: string;
  tasks_completed: number;
  tasks_failed: number;
  median_cycle_time_ms: number;
  completion_rate: number;
}

interface AgentMetricsResponse {
  agents: AgentMetrics[];
}

/**
 * Calculate median of an array of numbers
 */
function calculateMedian(values: number[]): number {
  if (values.length === 0) return 0;
  
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  
  if (sorted.length % 2 === 0) {
    return Math.round((sorted[mid - 1] + sorted[mid]) / 2);
  }
  return Math.round(sorted[mid]);
}

/**
 * Calculate cycle time for a completed task in milliseconds
 */
function getCycleTimeMs(task: { metadata: Record<string, unknown> }): number | null {
  const completedAt = task.metadata.completed_at;
  const startedAt = task.metadata.container_started_at;
  
  if (typeof completedAt === 'number' && typeof startedAt === 'number') {
    // Timestamps are in seconds, convert to milliseconds
    return (completedAt - startedAt) * 1000;
  }
  return null;
}

/**
 * Get agent_id from task metadata
 * Returns 'unassigned' if no agent_id is found
 */
function getAgentId(task: { metadata: Record<string, unknown> }): string {
  const agentId = task.metadata.agent_id;
  if (typeof agentId === 'string' && agentId.trim() !== '') {
    return agentId;
  }
  return 'unassigned';
}

async function handler(request: NextRequest): Promise<NextResponse> {
  try {
    const { searchParams } = new URL(request.url);
    const projectId = searchParams.get('project') || await getActiveProjectId();
    const daysParam = searchParams.get('days');
    const days = daysParam ? parseInt(daysParam, 10) : 30;

    // Validate days parameter
    if (isNaN(days) || days < 1) {
      return NextResponse.json(
        { error: 'Invalid days parameter' },
        { status: 400 }
      );
    }

    // Get all tasks for the project
    const tasks = await getTaskState(projectId);

    // Calculate the cutoff timestamp (days ago in seconds)
    const nowSeconds = Math.floor(Date.now() / 1000);
    const cutoffSeconds = nowSeconds - (days * 24 * 60 * 60);

    // Filter tasks within date range and group by agent
    const agentStats = new Map<
      string,
      {
        completed: number;
        failed: number;
        cycleTimes: number[];
      }
    >();

    // Initialize with all known agents from config (so agents with zero tasks appear)
    const allAgents = await listAgents();
    for (const agent of allAgents) {
      agentStats.set(agent.id, {
        completed: 0,
        failed: 0,
        cycleTimes: [],
      });
    }

    // Process tasks
    for (const task of tasks) {
      // Skip tasks outside the date range (use updated_at as the activity timestamp)
      const activityTimestamp = task.updated_at || task.created_at || 0;
      if (activityTimestamp < cutoffSeconds) {
        continue;
      }

      const agentId = getAgentId(task);

      // Initialize agent stats if not exists
      if (!agentStats.has(agentId)) {
        agentStats.set(agentId, {
          completed: 0,
          failed: 0,
          cycleTimes: [],
        });
      }

      const stats = agentStats.get(agentId)!;

      // Count by status
      switch (task.status) {
        case 'completed':
          stats.completed++;
          // Calculate cycle time for completed tasks
          const cycleTime = getCycleTimeMs(task);
          if (cycleTime !== null && cycleTime > 0) {
            stats.cycleTimes.push(cycleTime);
          }
          break;
        case 'failed':
        case 'rejected':
          stats.failed++;
          break;
        // pending, in_progress, starting, testing - don't count for completion metrics
      }
    }

    // Build response
    const agents: AgentMetrics[] = [];

    for (const [agentId, stats] of agentStats.entries()) {
      const totalCompletedFailed = stats.completed + stats.failed;
      const completionRate = totalCompletedFailed > 0
        ? Math.round((stats.completed / totalCompletedFailed) * 100) / 100
        : 0;

      agents.push({
        agent_id: agentId,
        tasks_completed: stats.completed,
        tasks_failed: stats.failed,
        median_cycle_time_ms: calculateMedian(stats.cycleTimes),
        completion_rate: completionRate,
      });
    }

    // Sort by tasks_completed descending (throughput)
    agents.sort((a, b) => b.tasks_completed - a.tasks_completed);

    const response: AgentMetricsResponse = { agents };

    return NextResponse.json(response);
  } catch (error) {
    console.error('Error loading agent metrics:', error);
    return NextResponse.json(
      { error: 'Failed to load agent metrics' },
      { status: 500 }
    );
  }
}

export const GET = withAuth(handler);
