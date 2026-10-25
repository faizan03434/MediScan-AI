import { useEffect } from 'react';
import { scheduleScanReminder, registerForPushNotificationsAsync } from './useNotifications';
import type { ScanResult } from '../types';
import { sessionVersion } from '../services/sessionEvents';

/**
 * Hook: auto-schedule a notification reminder when a scan has a nextScanDate.
 * Call this in the scan result screen.
 */
export function useScanReminder(scan: ScanResult | null) {
  useEffect(() => {
    if (!scan?.nextScanDate) return;
    const revision = sessionVersion(); let active = true;

    (async () => {
      const status = await registerForPushNotificationsAsync();
      if (active && revision === sessionVersion() && status === 'granted') {
        await scheduleScanReminder(scan);
      }
    })().catch(() => undefined);
    return () => { active = false; };
  }, [scan]);
}
