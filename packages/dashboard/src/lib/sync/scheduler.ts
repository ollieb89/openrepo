import { listConnectorStates } from '@/lib/connectors/store';
import { runIncrementalSync } from '@/lib/sync/engine';

export const BACKGROUND_SYNC_INTERVAL_MS = 3600000; // 1 hour

let isSyncRunning = false;

/**
 * Checks all connectors and triggers incremental sync for those that are:
 * 1. Enabled
 * 2. Not already syncing/rate-limited/auth-expired
 * 3. Haven't been synced in the last BACKGROUND_SYNC_INTERVAL_MS
 */
export async function runBackgroundSync() {
  if (isSyncRunning) {
    console.log('[Scheduler] Background sync check already in progress, skipping.');
    return { status: 'busy', triggered: [], skipped: 0 };
  }

  isSyncRunning = true;
  console.log('[Scheduler] Starting background sync check...');

  const triggered: string[] = [];
  let skipped = 0;

  try {
    const connectors = await listConnectorStates();
    const now = Date.now();

    for (const connector of connectors) {
      if (!connector.enabled) {
        skipped++;
        continue;
      }

      // Filter out connectors that shouldn't be touched by auto-scheduler
      if (['syncing', 'rate_limited', 'auth_expired'].includes(connector.status)) {
        console.log(`[Scheduler] Skipping connector ${connector.id} due to status: ${connector.status}`);
        skipped++;
        continue;
      }

      // Respect interval
      if (connector.lastSyncedAt) {
        const lastSyncedMs = new Date(connector.lastSyncedAt).getTime();
        if (now - lastSyncedMs < BACKGROUND_SYNC_INTERVAL_MS) {
          console.log(`[Scheduler] Skipping connector ${connector.id} - recently synced.`);
          skipped++;
          continue;
        }
      }

      console.log(`[Scheduler] Triggering background sync for ${connector.id}`);
      triggered.push(connector.id);
      
      // Fire and forget: We don't await the actual sync here so the scheduler
      // can finish quickly, but the connector status will move to 'syncing'
      // which prevents duplicate triggers in subsequent runs.
      runIncrementalSync({ connectorId: connector.id }).catch((err) => {
        console.error(`[Scheduler] Background sync failed for ${connector.id}:`, err);
      });
    }

    return { status: 'success', triggered, skipped };
  } catch (error) {
    console.error('[Scheduler] Error during background sync check:', error);
    return { status: 'error', triggered, skipped, error: String(error) };
  } finally {
    isSyncRunning = false;
    console.log(`[Scheduler] Background sync check finished. Triggered: ${triggered.length}, Skipped: ${skipped}`);
  }
}
