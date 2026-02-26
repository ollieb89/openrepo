'use client';

import { useEffect, useRef } from 'react';
import { toast } from 'react-toastify';
import { useSyncStatus, type SyncConnectorSnapshot, type SyncHealthStatus } from '@/lib/hooks/useSyncStatus';

function readStatusMessage(connector: SyncConnectorSnapshot): string {
  if (connector.status === 'auth_expired') {
    return `${connector.provider} sync blocked: authentication expired`;
  }
  if (connector.status === 'rate_limited') {
    return `${connector.provider} sync rate limited`;
  }
  if (connector.status === 'error') {
    return `${connector.provider} sync failed`;
  }
  if (connector.status === 'connected') {
    return `${connector.provider} sync completed`;
  }
  return `${connector.provider} sync status updated`;
}

function shouldShowToast(current: SyncHealthStatus, previous: SyncHealthStatus | undefined): boolean {
  if (!previous || previous === current) {
    return false;
  }

  return (
    current === 'connected' ||
    current === 'error' ||
    current === 'rate_limited' ||
    current === 'auth_expired'
  );
}

export default function SyncToast() {
  const { connectors } = useSyncStatus();
  const seen = useRef<Record<string, SyncHealthStatus>>({});
  const initialized = useRef(false);

  useEffect(() => {
    if (!initialized.current) {
      const initial: Record<string, SyncHealthStatus> = {};
      connectors.forEach(connector => {
        initial[connector.id] = connector.status;
      });
      seen.current = initial;
      initialized.current = true;
      return;
    }

    connectors.forEach(connector => {
      const previous = seen.current[connector.id];

      if (shouldShowToast(connector.status, previous)) {
        const message = readStatusMessage(connector);
        if (connector.status === 'connected') {
          toast.success(message);
        } else {
          toast.error(message);
        }
      }

      seen.current[connector.id] = connector.status;
    });
  }, [connectors]);

  return null;
}
