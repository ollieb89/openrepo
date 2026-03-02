/**
 * Token authentication endpoint
 * Allows clients to submit and validate tokens
 */

import { NextRequest, NextResponse } from 'next/server';
import { validateToken, isAuthRequired } from '@/lib/auth';

export async function POST(request: NextRequest): Promise<NextResponse> {
  // If auth not required, return success
  if (!isAuthRequired()) {
    return NextResponse.json(
      { authenticated: true, requiresAuth: false },
      { status: 200 }
    );
  }

  try {
    const body = await request.json();
    const { token } = body;

    if (!token) {
      return NextResponse.json(
        { error: 'Token is required', authenticated: false },
        { status: 400 }
      );
    }

    // Validate the submitted token
    if (validateToken(undefined, undefined, token)) {
      return NextResponse.json(
        { authenticated: true, message: 'Token accepted' },
        { status: 200 }
      );
    } else {
      return NextResponse.json(
        { error: 'Invalid token', authenticated: false },
        { status: 401 }
      );
    }
  } catch (error) {
    return NextResponse.json(
      { error: 'Invalid request body' },
      { status: 400 }
    );
  }
}

export async function GET(request: NextRequest): Promise<NextResponse> {
  // Check if auth is required
  if (!isAuthRequired()) {
    return NextResponse.json(
      { requiresAuth: false, authenticated: true },
      { status: 200 }
    );
  }

  // Check if current request has valid token
  const authHeader = request.headers.get('Authorization');
  const customTokenHeader = request.headers.get('X-OpenClaw-Token');

  const isValid = validateToken(
    authHeader || undefined,
    customTokenHeader || undefined
  );

  return NextResponse.json(
    {
      requiresAuth: true,
      authenticated: isValid,
    },
    { status: 200 }
  );
}
