import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock docker module
vi.mock('@/lib/docker', () => ({
  listOpenClawContainers: vi.fn().mockResolvedValue([
    { id: 'abc123', name: 'openclaw-proj-l3-task1', cpu_percent: 12.5, memory_mb: 256, status: 'running' }
  ])
}))

// Mock auth-middleware to allow through (no token required in tests)
vi.mock('@/lib/auth-middleware', () => ({
  withAuth: (handler: (req: Request) => Promise<Response>) => handler,
}))

describe('GET /api/containers', () => {
  beforeEach(() => {
    vi.resetModules()
  })

  it('test_returns_container_list_with_metrics: returns containers with cpu_percent and memory_mb', async () => {
    const { GET } = await import('@/app/api/containers/route')
    const req = new Request('http://localhost/api/containers')
    const res = await GET(req as never)
    const data = await res.json()
    expect(data.containers).toHaveLength(1)
    expect(data.containers[0]).toHaveProperty('cpu_percent')
    expect(data.containers[0]).toHaveProperty('memory_mb')
    expect(data.containers[0].cpu_percent).toBe(12.5)
    expect(data.containers[0].memory_mb).toBe(256)
  })

  it('test_returns_503_when_docker_unavailable: returns 503 with error field on docker failure', async () => {
    const docker = await import('@/lib/docker')
    vi.mocked(docker.listOpenClawContainers).mockRejectedValueOnce(new Error('Docker not available'))
    const { GET } = await import('@/app/api/containers/route')
    const req = new Request('http://localhost/api/containers')
    const res = await GET(req as never)
    expect(res.status).toBe(503)
    const data = await res.json()
    expect(data).toHaveProperty('error')
  })
})
