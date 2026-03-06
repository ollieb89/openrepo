import { NextRequest, NextResponse } from 'next/server';
import { getTaskState, getActiveProjectId } from '@/lib/openclaw';
import { withAuth } from '@/lib/auth-middleware';

export interface TrendPoint {
  date: string;
  completed: number;
  throughput: number;
}

export interface MetricsTrends {
  points: TrendPoint[];
  granularity: 'daily' | 'weekly' | 'monthly';
}

interface TrendsResponse {
  trends: MetricsTrends;
}

/**
 * Format a date for display based on granularity
 */
function formatDate(timestamp: number, granularity: 'daily' | 'weekly' | 'monthly'): string {
  const date = new Date(timestamp * 1000);
  
  switch (granularity) {
    case 'daily':
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    case 'weekly':
      return `Week ${getWeekNumber(date)}`;
    case 'monthly':
      return date.toLocaleDateString('en-US', { month: 'short', year: '2-digit' });
    default:
      return date.toLocaleDateString();
  }
}

/**
 * Get week number for a date
 */
function getWeekNumber(date: Date): number {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  const dayNum = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  return Math.ceil((((d.getTime() - yearStart.getTime()) / 86400000) + 1) / 7);
}

/**
 * Get the bucket key for a date based on granularity
 */
function getBucketKey(timestamp: number, granularity: 'daily' | 'weekly' | 'monthly'): string {
  const date = new Date(timestamp * 1000);
  
  switch (granularity) {
    case 'daily':
      return date.toISOString().split('T')[0]; // YYYY-MM-DD
    case 'weekly':
      return `${date.getFullYear()}-W${getWeekNumber(date)}`;
    case 'monthly':
      return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
    default:
      return date.toISOString().split('T')[0];
  }
}

async function handler(request: NextRequest): Promise<NextResponse> {
  try {
    const { searchParams } = new URL(request.url);
    const projectId = searchParams.get('project') || await getActiveProjectId();
    const daysParam = searchParams.get('days');
    const days = daysParam ? parseInt(daysParam, 10) : 7;
    const granularity = (searchParams.get('granularity') || 'daily') as 'daily' | 'weekly' | 'monthly';

    // Validate parameters
    if (isNaN(days) || days < 1) {
      return NextResponse.json(
        { error: 'Invalid days parameter' },
        { status: 400 }
      );
    }

    if (!['daily', 'weekly', 'monthly'].includes(granularity)) {
      return NextResponse.json(
        { error: 'Invalid granularity parameter' },
        { status: 400 }
      );
    }

    // Get all tasks for the project
    const tasks = await getTaskState(projectId);

    // Calculate the cutoff timestamp (days ago in seconds)
    const nowSeconds = Math.floor(Date.now() / 1000);
    const cutoffSeconds = daysParam ? nowSeconds - (days * 24 * 60 * 60) : 0;

    // Filter completed tasks within date range and bucket them
    const buckets = new Map<string, { completed: number; throughput: number }>();

    for (const task of tasks) {
      // Only include completed tasks
      if (task.status !== 'completed') continue;

      // Check if within date range — prefer metadata.completed_at, fall back to
      // top-level updated_at (set when the task transitions to 'completed') or
      // created_at as a last resort so tasks with metadata: {} are not dropped.
      const completedAt =
        (task.metadata?.completed_at as number | undefined) ??
        task.updated_at ??
        task.created_at;
      if (!completedAt) continue;
      
      if (daysParam && completedAt < cutoffSeconds) continue;
      
      // Get bucket key
      const bucketKey = getBucketKey(completedAt, granularity);
      
      if (!buckets.has(bucketKey)) {
        buckets.set(bucketKey, { completed: 0, throughput: 0 });
      }
      
      const bucket = buckets.get(bucketKey)!;
      bucket.completed++;
      bucket.throughput++; // Simplified: throughput = completed count
    }

    // Convert buckets to sorted points
    const sortedBuckets = Array.from(buckets.entries()).sort((a, b) => a[0].localeCompare(b[0]));
    
    // If no data, generate some sample points for the requested time range
    let points: TrendPoint[];
    
    if (sortedBuckets.length === 0) {
      // Generate empty data points for the range
      points = generateEmptyPoints(days, granularity, nowSeconds);
    } else {
      points = sortedBuckets.map(([key, data]) => ({
        date: formatDate(new Date(key).getTime() / 1000 || nowSeconds, granularity),
        completed: data.completed,
        throughput: data.throughput,
      }));
    }

    // Fill in gaps if needed for daily granularity
    if (granularity === 'daily' && points.length > 0) {
      points = fillDateGaps(points, days, nowSeconds);
    }

    const trends: MetricsTrends = {
      points,
      granularity,
    };

    const response: TrendsResponse = { trends };

    return NextResponse.json(response);
  } catch (error) {
    console.error('Error loading trends:', error);
    return NextResponse.json(
      { error: 'Failed to load trends' },
      { status: 500 }
    );
  }
}

/**
 * Generate empty points for a date range
 */
function generateEmptyPoints(
  days: number, 
  granularity: 'daily' | 'weekly' | 'monthly',
  nowSeconds: number
): TrendPoint[] {
  const points: TrendPoint[] = [];
  const numPoints = granularity === 'daily' ? days : granularity === 'weekly' ? Math.ceil(days / 7) : Math.ceil(days / 30);
  
  for (let i = numPoints - 1; i >= 0; i--) {
    const timestamp = nowSeconds - (i * (granularity === 'daily' ? 86400 : granularity === 'weekly' ? 604800 : 2592000));
    points.push({
      date: formatDate(timestamp, granularity),
      completed: 0,
      throughput: 0,
    });
  }
  
  return points;
}

/**
 * Fill in date gaps with zero values
 */
function fillDateGaps(points: TrendPoint[], days: number, nowSeconds: number): TrendPoint[] {
  const dateMap = new Map(points.map(p => [p.date, p]));
  const filled: TrendPoint[] = [];
  
  for (let i = days - 1; i >= 0; i--) {
    const timestamp = nowSeconds - (i * 86400);
    const dateStr = formatDate(timestamp, 'daily');
    
    if (dateMap.has(dateStr)) {
      filled.push(dateMap.get(dateStr)!);
    } else {
      filled.push({
        date: dateStr,
        completed: 0,
        throughput: 0,
      });
    }
  }
  
  return filled;
}

export const GET = withAuth(handler);
