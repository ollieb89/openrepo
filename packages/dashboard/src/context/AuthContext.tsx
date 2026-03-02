/**
 * Authentication context for OpenClaw Dashboard
 * Manages token storage and authentication state
 */

'use client';

import { createContext, useContext, useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { apiPath } from '@/lib/api-client';

interface AuthContextType {
  isAuthenticated: boolean;
  isLoading: boolean;
  token: string | null;
  login: (token: string) => Promise<void>;
  logout: () => void;
  requiresAuth: boolean | null;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const PUBLIC_ROUTES = new Set(['/login', '/api/auth/token']);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [token, setToken] = useState<string | null>(null);
  const [requiresAuth, setRequiresAuth] = useState<boolean | null>(null);
  const router = useRouter();
  const pathname = usePathname();

  // Check authentication status on mount and after token changes
  useEffect(() => {
    async function checkAuth() {
      try {
        // Check if auth is required
        const statusRes = await fetch(apiPath('/api/auth/token'));
        const statusData = await statusRes.json();
        setRequiresAuth(statusData.requiresAuth ?? false);

        if (statusData.requiresAuth === false) {
          // Auth not required, mark as authenticated
          setIsAuthenticated(true);
          setIsLoading(false);
          return;
        }

        // Auth is required, check if we have a token
        const storedToken = localStorage.getItem('openclaw_token');
        
        if (storedToken) {
          // Verify the stored token is still valid
          const verifyRes = await fetch(apiPath('/api/auth/token'), {
            headers: {
              'X-OpenClaw-Token': storedToken,
            },
          });

          if (verifyRes.ok) {
            setToken(storedToken);
            setIsAuthenticated(true);
          } else {
            // Token is invalid, clear it
            localStorage.removeItem('openclaw_token');
            setToken(null);
            setIsAuthenticated(false);
          }
        } else {
          setIsAuthenticated(false);
        }
      } catch (error) {
        console.error('Error checking authentication:', error);
        setIsAuthenticated(false);
      } finally {
        setIsLoading(false);
      }
    }

    checkAuth();
  }, []);

  // Redirect to login if not authenticated and on protected route
  useEffect(() => {
    if (isLoading) return; // Wait for initial check
    if (requiresAuth === null) return; // Wait for auth requirement check

    const isPublicRoute = PUBLIC_ROUTES.has(pathname);

    if (requiresAuth && !isAuthenticated && !isPublicRoute) {
      router.push('/login');
    } else if (!requiresAuth && pathname === '/login') {
      // Redirect away from login if auth not required
      router.push('/');
    }
  }, [isLoading, isAuthenticated, requiresAuth, pathname, router]);

  const login = async (newToken: string) => {
    try {
      const res = await fetch(apiPath('/api/auth/token'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: newToken }),
      });

      if (!res.ok) {
        throw new Error('Invalid token');
      }

      // Store and set token
      localStorage.setItem('openclaw_token', newToken);
      setToken(newToken);
      setIsAuthenticated(true);
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    }
  };

  const logout = () => {
    localStorage.removeItem('openclaw_token');
    setToken(null);
    setIsAuthenticated(false);
    router.push('/login');
  };

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated,
        isLoading,
        token,
        login,
        logout,
        requiresAuth: requiresAuth ?? false,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
