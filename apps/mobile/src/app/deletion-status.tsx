import React, { useEffect, useState } from 'react';
import { ScrollView, Text } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import Button from '../components/common/Button';
import { getDeletionStatus, type DeletionStatus } from '../services/accountDeletionService';
import { Colors } from '../theme/colors';

export default function DeletionStatusScreen() {
  const router = useRouter(); const [status, setStatus] = useState<DeletionStatus | null>(null);
  const [busy, setBusy] = useState(false); const [message, setMessage] = useState('');
  async function refresh() {
    setBusy(true); setMessage('');
    try { const result = await getDeletionStatus(); setStatus(result);
      if (!result) setMessage('No deletion receipt is saved on this device or browser tab.'); }
    catch { setMessage('Unable to check status right now. The server continues retrying queued cleanup. Please check again later.'); }
    finally { setBusy(false); }
  }
  useEffect(() => { void refresh(); }, []);
  return <SafeAreaView style={{ flex: 1, backgroundColor: Colors.bgDark }}>
    <ScrollView contentContainerStyle={{ padding: 24, gap: 20, maxWidth: 650, width: '100%', alignSelf: 'center' }}>
      <Text accessibilityRole="header" style={{ color: Colors.textPrimary, fontSize: 26, fontWeight: '800' }}>Account deletion status</Text>
      {status && <>
        <Text style={{ color: Colors.textPrimary, fontSize: 20, fontWeight: '700' }}>{status.status === 'completed' ? 'Live account cleanup completed' : 'Deletion queued'}</Text>
        <Text style={{ color: Colors.textSecondary, lineHeight: 23 }}>{status.status === 'completed'
          ? 'Your live account records and unshared photos have been removed. Backups, storage versions and copies shared outside the app follow separate retention policies.'
          : 'Your account access is disabled. Cleanup starts after a short delay and retries automatically if services are unavailable.'}</Text>
      </>}
      {!!message && <Text accessibilityLiveRegion="polite" style={{ color: Colors.textSecondary }}>{message}</Text>}
      <Button title="Refresh status" variant="outline" loading={busy} onPress={refresh} />
      <Button title="Go to sign in" onPress={() => router.replace('/(auth)/login')} />
    </ScrollView>
  </SafeAreaView>;
}
