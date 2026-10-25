import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';
import type { ScanResult } from '../types';
import { onSessionCleared, sessionVersion } from '../services/sessionEvents';

const PREFIX = 'scan_reminder_';
let notificationWork: Promise<void> = Promise.resolve();
const serial = <T>(operation: () => Promise<T>): Promise<T> => {
  const next = notificationWork.then(operation);
  notificationWork = next.then(() => undefined, () => undefined);
  return next;
};
async function clearScanNotifications(scanType?: string, legacyOnly = false) {
  if (Platform.OS === 'web') return;
  const matches = (id: string) => id.startsWith(PREFIX) && (!legacyOnly || /^scan_reminder_[A-Za-z]/.test(id)) && (!scanType || id.endsWith(`_${scanType}`) || id === PREFIX + scanType);
  for (const request of await Notifications.getAllScheduledNotificationsAsync()) {
    if (matches(request.identifier)) await Notifications.cancelScheduledNotificationAsync(request.identifier);
  }
  for (const notification of await Notifications.getPresentedNotificationsAsync()) {
    if (matches(notification.request.identifier)) await Notifications.dismissNotificationAsync(notification.request.identifier);
  }
}

// Configure how notifications appear when app is foregrounded
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldShowBanner: true,
    shouldShowList: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

async function requestNotificationPermission(): Promise<string | null> {
  if (Platform.OS === 'web') return null;
  // expo-device check: skip on web/simulator
  let isDevice = true;
  try {
    const Device = await import('expo-device');
    isDevice = Device.isDevice;
  } catch { /* not available */ }

  if (!isDevice) return null;

  const { status: existingStatus } = await Notifications.getPermissionsAsync();
  let finalStatus = existingStatus;

  if (existingStatus !== 'granted') {
    const { status } = await Notifications.requestPermissionsAsync();
    finalStatus = status;
  }

  if (finalStatus !== 'granted') return null;

  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync('mediscan_reminders', {
      name: 'MediScan Reminders',
      importance: Notifications.AndroidImportance.HIGH,
      vibrationPattern: [0, 250, 250, 250],
      lightColor: '#3B82F6',
    });
  }

  return 'granted';
}

export async function registerForPushNotificationsAsync(): Promise<string | null> {
  try { return await requestNotificationPermission(); } catch { return null; }
}

/**
 * Schedule a local notification reminder for a re-scan.
 * Called after a scan result is saved.
 */
export async function scheduleScanReminder(scan: ScanResult): Promise<void> {
  if (Platform.OS === 'web' || !scan.nextScanDate) return;

  const nextDate = new Date(scan.nextScanDate);
  if (!Number.isFinite(nextDate.getTime()) || nextDate <= new Date()) return;
  const revision = sessionVersion();
  await serial(async () => {
    if (revision !== sessionVersion()) return;
    await clearScanNotifications(scan.scanType);
    if (revision !== sessionVersion()) return;
    await Notifications.scheduleNotificationAsync({
    identifier: `${PREFIX}${revision}_${scan.scanType}`,
    content: {
      title: 'MediScan reminder',
      body: 'Open MediScan to review your saved follow-up reminder.',
      data: { kind: 'scan_reminder' },
      sound: true,
    },
    trigger: {
      type: Notifications.SchedulableTriggerInputTypes.DATE,
      date: nextDate,
    },
    });
  });
}

export async function cancelScanReminder(scanType: string): Promise<void> {
  await serial(() => clearScanNotifications(scanType));
}

export async function cancelAllReminders(): Promise<void> {
  await serial(() => clearScanNotifications());
}

export async function getScheduledReminders() {
  await notificationWork;
  return Platform.OS === 'web' ? [] : (await Notifications.getAllScheduledNotificationsAsync()).filter(item => item.identifier.startsWith(PREFIX));
}

onSessionCleared(() => { void cancelAllReminders().catch(() => undefined); });
// Remove prior-version reminders whose OS-visible payload could include condition names.
void serial(() => clearScanNotifications(undefined, true)).catch(() => undefined);
