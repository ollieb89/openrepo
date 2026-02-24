import { NextRequest } from 'next/server';
import { readOpenClawConfig } from '@/lib/openclaw';

async function getMemuUrl(): Promise<string> {
  const config = await readOpenClawConfig();
  const memory = config.memory as Record<string, string> | undefined;
  return memory?.memu_api_url ?? 'http://localhost:18791';
}

export async function DELETE(
  _request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const memuUrl = await getMemuUrl();
    const res = await fetch(`${memuUrl}/memories/${params.id}`, { method: 'DELETE' });
    if (!res.ok) {
      return Response.json({ error: 'Delete failed' }, { status: res.status });
    }
    const data = await res.json();
    return Response.json(data);
  } catch (error) {
    console.error('Error deleting memory:', error);
    return Response.json({ error: 'Failed to delete memory item' }, { status: 500 });
  }
}
