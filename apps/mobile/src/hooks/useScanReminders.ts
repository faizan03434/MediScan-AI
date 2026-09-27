import { useEffect } from 'react';
import { scheduleScanReminder, registerForPushNotificationsAsync } from './useNotifications';
import type { ScanResult } from '../types';

/**
 * Hook: auto-schedule a notification reminder when a scan has a nextScanDate.
 * Call this in the scan result screen.
 */
export function useScanReminder(scan: ScanResult | null) {
  useEffect(() => {
    if (!scan?.nextScanDate) return;

    (async () => {
      const status = await registerForPushNotificationsAsync();
      if (status === 'granted') {
        await scheduleScanReminder(scan);
      }
    })();
  }, [scan?.id]);
}
