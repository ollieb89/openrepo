'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { apiPath } from '@/lib/api-client';

export default function LoginPage() {
  const [token, setToken] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [requiresAuth, setRequiresAuth] = useState<boolean | null>(null);
  const router = useRouter();

  // Check if auth is required on mount
  useEffect(() => {
    async function checkAuthRequired() {
      try {
        const res = await fetch(apiPath('/api/auth/token'));
        const data = await res.json();
        setRequiresAuth(data.requiresAuth);
        
        // If auth not required and user somehow got to login, redirect home
        if (data.requiresAuth === false) {
          router.push('/');
        }
      } catch (err) {
        console.error('Error checking auth requirement:', err);
        setRequiresAuth(true); // Assume auth required on error
      }
    }
    checkAuthRequired();
  }, [router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      const res = await fetch(apiPath('/api/auth/token'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token }),
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.error || 'Authentication failed');
        return;
      }

      // Store token in localStorage
      localStorage.setItem('openclaw_token', token);

      // Redirect to home
      router.push('/');
    } catch (err) {
      setError('Network error. Please try again.');
      console.error('Error during authentication:', err);
    } finally {
      setIsLoading(false);
    }
  };

  if (requiresAuth === null) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50 dark:bg-gray-900">
        <div className="text-gray-600 dark:text-gray-400">Loading...</div>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="w-full max-w-md">
        <div className="bg-white dark:bg-gray-800 shadow-md rounded-lg p-8">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">
            OpenClaw Dashboard
          </h1>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
            Enter your authentication token to continue
          </p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="token" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Authentication Token
              </label>
              <input
                id="token"
                type="password"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                placeholder="Enter your token"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg bg-white dark:bg-gray-700 dark:border-gray-600 text-gray-900 dark:text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={isLoading}
              />
            </div>

            {error && (
              <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded text-sm text-red-700 dark:text-red-400">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading || !token.trim()}
              className="w-full py-2 px-4 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-medium rounded-lg transition"
            >
              {isLoading ? 'Verifying...' : 'Login'}
            </button>
          </form>

          <p className="text-xs text-gray-500 dark:text-gray-500 mt-6">
            The token is stored securely in your browser&apos;s local storage. For production, consider using HTTPS and a session-based authentication system.
          </p>
        </div>
      </div>
    </div>
  );
}
