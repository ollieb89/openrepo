/**
 * Next.js middleware for OpenClaw Dashboard authentication
 * Apply to all API routes to enforce token validation
 */

import { NextRequest, NextResponse } from 'next/server';
import { validateToken, isAuthRequired } from './auth';

export interface AuthMiddlewareOptions {
  // Routes that don't require authentication
  publicRoutes?: string[];
  // Custom error response
  onAuthError?: (req: NextRequest) => NextResponse;
}

const DEFAULT_PUBLIC_ROUTES = [
  '/api/health',
  '/api/auth/token', // For token submission
];

/**
 * Create an authentication middleware for API routes
 * 
 * Usage in route.ts:
 * ```
 * const authMiddleware = createAuthMiddleware({ publicRoutes: ['/api/health'] });
 * 
 * export async function GET(request: NextRequest) {
 *   const auth = authMiddleware(request);
 *   if (!auth.ok) return auth;
 *   // ... rest of handler
 * }
 * ```
 */
export function createAuthMiddleware(options: AuthMiddlewareOptions = {}) {
  const publicRoutes = new Set([...DEFAULT_PUBLIC_ROUTES, ...(options.publicRoutes || [])]);

  return (request: NextRequest): NextResponse | null => {
    const pathname = new URL(request.url).pathname;

    // Skip auth check for public routes
    if (publicRoutes.has(pathname)) {
      return null;
    }

    // If auth not required globally, allow all
    if (!isAuthRequired()) {
      return null;
    }

    // Extract token from various sources
    const authHeader = request.headers.get('Authorization');
    const customTokenHeader = request.headers.get('X-OpenClaw-Token');
    const queryToken = new URL(request.url).searchParams.get('_token') || undefined;

    // Validate token
    if (!validateToken(authHeader || undefined, customTokenHeader || undefined, queryToken)) {
      if (options.onAuthError) {
        return options.onAuthError(request);
      }

      return createUnauthorizedResponse();
    }

    // Auth passed, return null to continue with handler
    return null;
  };
}

/**
 * Create a standard 401 Unauthorized response
 */
export function createUnauthorizedResponse(): NextResponse {
  return NextResponse.json(
    {
      error: 'Unauthorized',
      message: 'Missing or invalid authentication token',
      hint: 'Provide token via: Authorization: Bearer <token> header or X-OpenClaw-Token header',
    },
    { status: 401 }
  );
}

/**
 * Apply auth middleware as a wrapper around a handler
 * 
 * Usage:
 * ```
 * async function handler(request: NextRequest) {
 *   // ... your logic
 * }
 * 
 * export const GET = withAuth(handler);
 * ```
 */
export function withAuth(
  handler: (request: NextRequest, ...args: any[]) => Promise<Response> | Response,
  options: AuthMiddlewareOptions = {}
) {
  const authMiddleware = createAuthMiddleware(options);

  return async (request: NextRequest, ...args: any[]): Promise<Response> => {
    const authResponse = authMiddleware(request);
    if (authResponse) return authResponse;
    return handler(request, ...args);
  };
}
