import { NextRequest, NextResponse } from 'next/server';
import { readOpenClawConfig } from '@/lib/openclaw';
import { withAuth } from '@/lib/auth-middleware';

async function getMemuUrl(): Promise<string> {
  const config = await readOpenClawConfig();
  const memory = config.memory as Record<string, string> | undefined;
  return memory?.memu_api_url ?? 'http://localhost:18791';
}

async function deleteHandler(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const memuUrl = await getMemuUrl();
    const res = await fetch(`${memuUrl}/memories/${id}`, { method: 'DELETE' });
    if (!res.ok) {
      return NextResponse.json({ error: 'Delete failed' }, { status: res.status });
    }
    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error deleting memory:', error);
    return NextResponse.json({ error: 'Failed to delete memory item' }, { status: 500 });
  }
}

async function putHandler(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const memuUrl = await getMemuUrl();
    const body = await request.json();
    const res = await fetch(`${memuUrl}/memories/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      return NextResponse.json({ error: 'Update failed' }, { status: res.status });
    }
    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error updating memory:', error);
    return NextResponse.json({ error: 'Failed to update memory item' }, { status: 500 });
  }
}

export const DELETE = withAuth(deleteHandler);
export const PUT = withAuth(putHandler);
