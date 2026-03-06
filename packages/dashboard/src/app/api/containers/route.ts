import { NextRequest, NextResponse } from 'next/server'
import { withAuth } from '@/lib/auth-middleware'
import { listOpenClawContainers } from '@/lib/docker'

async function handler(_request: NextRequest) {
  try {
    const containers = await listOpenClawContainers()
    return NextResponse.json({ containers })
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : 'docker unavailable' },
      { status: 503 }
    )
  }
}

export const GET = withAuth(handler)
