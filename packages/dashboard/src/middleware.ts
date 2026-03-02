/**
 * Next.js middleware for authentication
 * Runs on every request to enforce token validation
 */

import { NextRequest, NextResponse } from 'next/server';
import { validateToken, isAuthRequired } from '@/lib/auth';

// Routes that don't require authentication
const PUBLIC_ROUTES = new Set([
  '/login',
  '/api/auth/token',
  '/api/health',
]);

// Static assets and Next.js internals
const EXCLUDE_PATTERNS = [
  '/_next',
  '/favicon.ico',
  '/public',
];

export function middleware(request: NextRequest) {
  const pathname = new URL(request.url).pathname;

  // Skip middleware for static files and Next.js internals
  if (EXCLUDE_PATTERNS.some(pattern => pathname.startsWith(pattern))) {
    return NextResponse.next();
  }

  // Get auth requirement and token
  const expectedToken = process.env.OPENCLAW_GATEWAY_TOKEN;
  const authRequired = !!expectedToken;

  // If auth not required, allow all
  if (!authRequired) {
    return NextResponse.next();
  }

  // Check if route is public
  if (PUBLIC_ROUTES.has(pathname)) {
    return NextResponse.next();
  }

  // Extract token from various sources
  const authHeader = request.headers.get('Authorization');
  const customTokenHeader = request.headers.get('X-OpenClaw-Token');
  const queryToken = new URL(request.url).searchParams.get('_token');

  // For API routes, check token in headers
  if (pathname.startsWith('/api/')) {
    if (!validateToken(authHeader || undefined, customTokenHeader || undefined, queryToken || undefined)) {
      return NextResponse.json(
        {
          error: 'Unauthorized',
          message: 'Missing or invalid authentication token',
        },
        { status: 401 }
      );
    }
    return NextResponse.next();
  }

  // For page routes, check if user is authenticated
  // The authentication token is stored in a secure cookie or localStorage (client-side)
  // For now, we'll let the client-side layout handle redirection
  // In a production system, you'd use secure cookies that the server can validate
  return NextResponse.next();
}

// Configure which routes the middleware runs on
export const config = {
  matcher: [
    // Skip static files
    '/((?!_next/static|_next/image|favicon.ico).*)',
  ],
};
