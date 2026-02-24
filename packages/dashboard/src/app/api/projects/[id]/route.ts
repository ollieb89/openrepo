import { getProject } from '@/lib/openclaw';

export async function GET(
  _request: Request,
  { params }: { params: { id: string } }
) {
  try {
    const project = await getProject(params.id);
    if (!project) {
      return Response.json({ error: 'Project not found' }, { status: 404 });
    }
    return Response.json({ project });
  } catch (error) {
    console.error('Error loading project:', error);
    return Response.json({ error: 'Failed to load project' }, { status: 500 });
  }
}
