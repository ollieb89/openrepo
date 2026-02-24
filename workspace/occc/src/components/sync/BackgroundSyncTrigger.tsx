'use client';

import { useEffect } from 'react';

/**
 * Client-side component that pings the background sync API periodically.
 * Renders nothing, intended to be mounted in the root layout.
 */
export default function BackgroundSyncTrigger() {
  useEffect(() => {
    // Initial ping on mount
    const triggerSync = async () => {
      try {
        await fetch('/api/connectors/sync/background', {
          method: 'POST',
        });
      } catch (err) {
        // Silent fail for background trigger
        console.warn('[SyncTrigger] Failed to ping background sync:', err);
      }
    };

    triggerSync();

    // Set up periodic heartbeat (every 5 minutes)
    const interval = setInterval(() => {
      // Only trigger if document is visible to avoid overhead in background tabs
      if (document.visibilityState === 'visible') {
        triggerSync();
      }
    }, 300000);

    return () => clearInterval(interval);
  }, []);

  return null;
}
