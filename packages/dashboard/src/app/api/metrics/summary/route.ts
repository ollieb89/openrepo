import { NextRequest, NextResponse } from 'next/server';
import { getTaskState, getActiveProjectId } from '@/lib/openclaw';
import { withAuth } from '@/lib/auth-middleware';

interface MetricsSummary {
  completion_rate: number;
  completion_trend: 'up' | 'down' | 'neutral';
  completion_trend_value: string;
  throughput: number;
  throughput_trend: 'up' | 'down' | 'neutral';
  throughput_trend_value: string;
  cycle_time_ms: number;
  cycle_time_trend: 'up' | 'down' | 'neutral';
  cycle_time_trend_value: string;
  wip_count: number;
  wip_trend: 'up' | 'down' | 'neutral';
  wip_trend_value: string;
  failure_rate: number;
  failure_trend: 'up' | 'down' | 'neutral';
  failure_trend_value: string;
}

interface SummaryResponse {
  summary: MetricsSummary;
}

/**
 * Calculate trend with simulated variation
 * In production, this would compare with historical data
 */
function calculateTrend(currentValue: number): { trend: 'up' | 'down' | 'neutral'; trendValue: string } {
  // Simulate trend with small random variation (-10% to +10%)
  const variation = (Math.random() - 0.5) * 0.2;
  const previousValue = currentValue * (1 - variation);
  const percentChange = previousValue !== 0 
    ? ((currentValue - previousValue) / previousValue) * 100 
    : 0;
  
  let trend: 'up' | 'down' | 'neutral';
  if (Math.abs(percentChange) < 1) {
    trend = 'neutral';
  } else if (percentChange > 0) {
    trend = 'up';
  } else {
    trend = 'down';
  }
  
  const trendValue = `${Math.abs(percentChange).toFixed(0)}%`;
  
  return { trend, trendValue };
}

/**
 * Calculate cycle time for a completed task in milliseconds
 */
function getCycleTimeMs(task: { metadata: Record<string, unknown> }): number | null {
  const completedAt = task.metadata.completed_at;
  const startedAt = task.metadata.container_started_at;
  
  if (typeof completedAt === 'number' && typeof startedAt === 'number') {
    return (completedAt - startedAt) * 1000;
  }
  return null;
}

async function handler(request: NextRequest): Promise<NextResponse> {
  try {
    const { searchParams } = new URL(request.url);
    const projectId = searchParams.get('project') || await getActiveProjectId();
    const daysParam = searchParams.get('days');
    const days = daysParam ? parseInt(daysParam, 10) : 7;

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
    const cutoffSeconds = daysParam ? nowSeconds - (days * 24 * 60 * 60) : 0;

    // Filter tasks within date range
    const filteredTasks = tasks.filter(task => {
      if (!daysParam) return true; // All time
      const activityTimestamp = task.updated_at || task.created_at || 0;
      return activityTimestamp >= cutoffSeconds;
    });

    // Calculate metrics
    let completedCount = 0;
    let failedCount = 0;
    let wipCount = 0;
    const cycleTimes: number[] = [];

    for (const task of filteredTasks) {
      switch (task.status) {
        case 'completed':
          completedCount++;
          const cycleTime = getCycleTimeMs(task);
          if (cycleTime !== null && cycleTime > 0) {
            cycleTimes.push(cycleTime);
          }
          break;
        case 'failed':
        case 'rejected':
          failedCount++;
          break;
        case 'in_progress':
        case 'starting':
        case 'testing':
          wipCount++;
          break;
      }
    }

    const totalCompletedFailed = completedCount + failedCount;
    const completionRate = totalCompletedFailed > 0 
      ? completedCount / totalCompletedFailed 
      : 0;
    const failureRate = totalCompletedFailed > 0 
      ? failedCount / totalCompletedFailed 
      : 0;
    
    // Calculate average cycle time
    const avgCycleTimeMs = cycleTimes.length > 0
      ? Math.round(cycleTimes.reduce((a, b) => a + b, 0) / cycleTimes.length)
      : 0;

    // Calculate trends
    const completionTrend = calculateTrend(completionRate);
    const throughputTrend = calculateTrend(completedCount);
    const cycleTimeTrend = calculateTrend(avgCycleTimeMs);
    const wipTrend = calculateTrend(wipCount);
    const failureTrend = calculateTrend(failureRate);

    const summary: MetricsSummary = {
      completion_rate: completionRate,
      completion_trend: completionTrend.trend,
      completion_trend_value: completionTrend.trendValue,
      throughput: completedCount,
      throughput_trend: throughputTrend.trend,
      throughput_trend_value: throughputTrend.trendValue,
      cycle_time_ms: avgCycleTimeMs,
      cycle_time_trend: cycleTimeTrend.trend,
      cycle_time_trend_value: cycleTimeTrend.trendValue,
      wip_count: wipCount,
      wip_trend: wipTrend.trend,
      wip_trend_value: wipTrend.trendValue,
      failure_rate: failureRate,
      failure_trend: failureTrend.trend,
      failure_trend_value: failureTrend.trendValue,
    };

    const response: SummaryResponse = { summary };

    return NextResponse.json(response);
  } catch (error) {
    console.error('Error loading metrics summary:', error);
    return NextResponse.json(
      { error: 'Failed to load metrics summary' },
      { status: 500 }
    );
  }
}

export const GET = withAuth(handler);
