import { NextRequest } from 'next/server';
import { readOpenClawConfig, getActiveProjectId } from '@/lib/openclaw';

async function getMemuUrl(): Promise<string> {
  const config = await readOpenClawConfig();
  const memory = config.memory as Record<string, string> | undefined;
  return memory?.memu_api_url ?? 'http://localhost:18791';
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const projectId = searchParams.get('project') || await getActiveProjectId();
    const search = searchParams.get('search');

    const memuUrl = await getMemuUrl();

    if (search) {
      const res = await fetch(`${memuUrl}/retrieve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          queries: [{ role: 'user', content: search }],
          where: { user_id: projectId },
        }),
      });
      const data = await res.json();
      const items = Array.isArray(data) ? data : (data.items ?? []);
      return Response.json({ items, total: items.length, projectId, mode: 'search' });
    } else {
      const res = await fetch(`${memuUrl}/memories?user_id=${encodeURIComponent(projectId)}`);
      const data = await res.json();
      const items = Array.isArray(data) ? data : (data.items ?? []);
      return Response.json({ items, total: items.length, projectId, mode: 'browse' });
    }
  } catch (error) {
    console.error('Error fetching memories:', error);
    return Response.json({ error: 'Failed to fetch memories' }, { status: 500 });
  }
}
