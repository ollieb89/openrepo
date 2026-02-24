import { listProjects, getActiveProjectId } from '@/lib/openclaw';

export async function GET() {
  try {
    const [projects, activeId] = await Promise.all([
      listProjects(),
      getActiveProjectId(),
    ]);
    return Response.json({ projects, activeId });
  } catch (error) {
    console.error('Error loading projects:', error);
    return Response.json({ error: 'Failed to load projects' }, { status: 500 });
  }
}
