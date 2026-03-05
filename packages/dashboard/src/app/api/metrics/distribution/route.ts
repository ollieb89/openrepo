import { NextRequest, NextResponse } from 'next/server';
import { getTaskState, getActiveProjectId } from '@/lib/openclaw';
import { withAuth } from '@/lib/auth-middleware';
import type { TaskStatus } from '@/lib/types';

interface StatusDistributionPoint {
  date: string;
  completed: number;
  failed: number;
  pending: number;
  in_progress: number;
}

interface DistributionResponse {
  distribution: StatusDistributionPoint[];
}

/**
 * Format a date for display
 */
function formatDate(timestamp: number): string {
  const date = new Date(timestamp * 1000);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

/**
 * Get the bucket key for a date
 */
function getBucketKey(timestamp: number): string {
  const date = new Date(timestamp * 1000);
  return date.toISOString().split('T')[0]; // YYYY-MM-DD
}

async function handler(request: NextRequest): Promise<NextResponse> {
  try {
    const { searchParams } = new URL(request.url);
    const projectId = searchParams.get('project') || await getActiveProjectId();
    const daysParam = searchParams.get('days');
    const days = daysParam ? parseInt(daysParam, 10) : 7;

    // Validate parameters
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

    // Bucket tasks by date and status
    const buckets = new Map<string, { 
      completed: number; 
      failed: number; 
      pending: number; 
      in_progress: number;
    }>();

    for (const task of tasks) {
      // Get the relevant timestamp for the task
      const timestamp = task.updated_at || task.created_at || 0;
      
      // Check if within date range
      if (daysParam && timestamp < cutoffSeconds) continue;
      
      // Get bucket key
      const bucketKey = getBucketKey(timestamp);
      
      if (!buckets.has(bucketKey)) {
        buckets.set(bucketKey, { 
          completed: 0, 
          failed: 0, 
          pending: 0, 
          in_progress: 0 
        });
      }
      
      const bucket = buckets.get(bucketKey)!;
      
      // Count by status
      switch (task.status) {
        case 'completed':
          bucket.completed++;
          break;
        case 'failed':
        case 'rejected':
          bucket.failed++;
          break;
        case 'pending':
          bucket.pending++;
          break;
        case 'in_progress':
        case 'starting':
        case 'testing':
          bucket.in_progress++;
          break;
      }
    }

    // Convert buckets to sorted points
    const sortedBuckets = Array.from(buckets.entries()).sort((a, b) => a[0].localeCompare(b[0]));
    
    // If no data, generate empty points for the range
    let distribution: StatusDistributionPoint[];
    
    if (sortedBuckets.length === 0) {
      distribution = generateEmptyPoints(days, nowSeconds);
    } else {
      distribution = sortedBuckets.map(([key, data]) => ({
        date: formatDate(new Date(key).getTime() / 1000),
        completed: data.completed,
        failed: data.failed,
        pending: data.pending,
        in_progress: data.in_progress,
      }));
    }

    // Fill in gaps to ensure continuous date range
    distribution = fillDateGaps(distribution, days, nowSeconds);

    const response: DistributionResponse = { distribution };

    return NextResponse.json(response);
  } catch (error) {
    console.error('Error loading status distribution:', error);
    return NextResponse.json(
      { error: 'Failed to load status distribution' },
      { status: 500 }
    );
  }
}

/**
 * Generate empty points for a date range
 */
function generateEmptyPoints(days: number, nowSeconds: number): StatusDistributionPoint[] {
  const points: StatusDistributionPoint[] = [];
  
  for (let i = days - 1; i >= 0; i--) {
    const timestamp = nowSeconds - (i * 86400);
    points.push({
      date: formatDate(timestamp),
      completed: 0,
      failed: 0,
      pending: 0,
      in_progress: 0,
    });
  }
  
  return points;
}

/**
 * Fill in date gaps with zero values
 */
function fillDateGaps(
  points: StatusDistributionPoint[], 
  days: number, 
  nowSeconds: number
): StatusDistributionPoint[] {
  const dateMap = new Map(points.map(p => [p.date, p]));
  const filled: StatusDistributionPoint[] = [];
  
  for (let i = days - 1; i >= 0; i--) {
    const timestamp = nowSeconds - (i * 86400);
    const dateStr = formatDate(timestamp);
    
    if (dateMap.has(dateStr)) {
      filled.push(dateMap.get(dateStr)!);
    } else {
      filled.push({
        date: dateStr,
        completed: 0,
        failed: 0,
        pending: 0,
        in_progress: 0,
      });
    }
  }
  
  return filled;
}

export const GET = withAuth(handler);
