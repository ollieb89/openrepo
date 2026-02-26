import { getActiveProjectId, getProject } from '@/lib/openclaw';

export async function GET() {
  try {
    const id = await getActiveProjectId();
    const project = await getProject(id);
    return Response.json({ id, project });
  } catch (error) {
    console.error('Error loading active project:', error);
    return Response.json({ error: 'Failed to load active project' }, { status: 500 });
  }
}
