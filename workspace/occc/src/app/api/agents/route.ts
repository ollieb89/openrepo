import { listAgents } from '@/lib/openclaw';

export async function GET() {
  try {
    const agents = await listAgents();
    return Response.json({ agents });
  } catch (error) {
    console.error('Error loading agents:', error);
    return Response.json({ error: 'Failed to load agents' }, { status: 500 });
  }
}
