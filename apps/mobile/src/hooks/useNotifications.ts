import { useEffect } from 'react';
import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';
import type { ScanResult } from '../types';

// Configure how notifications appear when app is foregrounded
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

export async function registerForPushNotificationsAsync(): Promise<string | null> {
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

/**
 * Schedule a local notification reminder for a re-scan.
 * Called after a scan result is saved.
 */
export async function scheduleScanReminder(scan: ScanResult): Promise<void> {
  if (!scan.nextScanDate) return;

  const nextDate = new Date(scan.nextScanDate);
  if (nextDate <= new Date()) return; // already past

  // Cancel any existing reminder for this scan type
  await cancelScanReminder(scan.scanType);

  const scanLabels: Record<string, string> = {
    Anemia:          'Anemia Check',
    SkinDisease:     'Skin Scan',
    Posture:         'Posture Check',
    EyeDisease:      'Eye Scan',
    Wound:           'Wound Check',
    TongueDiagnosis: 'Tongue Check',
  };

  await Notifications.scheduleNotificationAsync({
    identifier: `scan_reminder_${scan.scanType}`,
    content: {
      title: `⏰ Time for your ${scanLabels[scan.scanType] ?? 'Health Scan'}`,
      body: `${scan.nextScanRecommendation ?? 'Your scheduled rescan is due today.'} Open MediScan AI to scan now.`,
      data: { scanType: scan.scanType, scanId: scan.id },
      sound: true,
    },
    trigger: {
      date: nextDate,
    },
  });
}

export async function cancelScanReminder(scanType: string): Promise<void> {
  await Notifications.cancelScheduledNotificationAsync(`scan_reminder_${scanType}`);
}

export async function cancelAllReminders(): Promise<void> {
  await Notifications.cancelAllScheduledNotificationsAsync();
}

export async function getScheduledReminders() {
  return await Notifications.getAllScheduledNotificationsAsync();
}
