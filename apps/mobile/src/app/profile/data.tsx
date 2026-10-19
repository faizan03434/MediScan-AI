import React, { useState } from 'react';
import { Platform, ScrollView, Share, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { useQueryClient } from '@tanstack/react-query';
import Button from '../../components/common/Button';
import { exportAccountData, revokeAllSessions } from '../../services/accountDataService';
import useAuthStore from '../../store/authStore';
import { Colors } from '../../theme/colors';

export default function AccountDataScreen() {
  const router = useRouter(); const cache = useQueryClient();
  const [busy, setBusy] = useState<'export' | 'logout' | null>(null);
  const [confirm, setConfirm] = useState(false); const [message, setMessage] = useState('');
  async function download() {
    setBusy('export'); setMessage('');
    try {
      const json = await exportAccountData();
      if (Platform.OS === 'web') {
        const url = URL.createObjectURL(new Blob([json], { type: 'application/json' }));
        const link = document.createElement('a'); link.href = url; link.download = 'mediscan-account.json'; link.click();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
      } else {
        const result = await Share.share({ title: 'MediScan account export', message: json });
        if (result.action === Share.dismissedAction) return;
      }
      setMessage('Export prepared. Photos are available separately in your scan history.');
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Export failed. Please retry.'); }
    finally { setBusy(null); }
  }
  async function signOutEverywhere() {
    setBusy('logout'); setMessage('');
    try {
      await revokeAllSessions(); cache.clear();
      await useAuthStore.getState().logout(); router.replace('/(auth)/login');
    } catch { setMessage('Could not confirm sign out on all devices. Please retry.'); }
    finally { setBusy(null); }
  }
  return <SafeAreaView style={{ flex: 1, backgroundColor: Colors.bgDark }}>
    <ScrollView contentContainerStyle={{ padding: 20, gap: 20, maxWidth: 700, width: '100%', alignSelf: 'center' }}>
      <Button title="Back to profile" variant="ghost" onPress={() => router.back()} />
      <Text accessibilityRole="header" style={{ fontSize: 26, fontWeight: '800', color: Colors.textPrimary }}>Your data & sessions</Text>
      <View style={{ padding: 20, borderRadius: 18, gap: 14, backgroundColor: Colors.bgCard, borderWidth: 1, borderColor: Colors.border }}>
        <Text style={{ color: Colors.textPrimary, fontSize: 19, fontWeight: '700' }}>Export your records</Text>
        <Text style={{ color: Colors.textSecondary, lineHeight: 22 }}>Download or share your profile, scan results, medications, prescription text and doctor consent records as JSON. This includes retained records you previously removed from history. Photos and login credentials are excluded.</Text>
        <Text style={{ color: Colors.textSecondary, lineHeight: 22 }}>The export contains private health information. Choose a destination you trust. Records added or changed while exporting may require a fresh export.</Text>
        <Button title={Platform.OS === 'web' ? 'Download my data' : 'Share my data export'} loading={busy === 'export'} disabled={busy !== null} onPress={download} />
      </View>
      <View style={{ padding: 20, borderRadius: 18, gap: 14, backgroundColor: Colors.bgCard, borderWidth: 1, borderColor: Colors.border }}>
        <Text style={{ color: Colors.textPrimary, fontSize: 19, fontWeight: '700' }}>Sign out on every device</Text>
        <Text style={{ color: Colors.textSecondary, lineHeight: 22 }}>End your current sessions on all phones and browsers. You will need to sign in again on this device.</Text>
        {confirm ? <><Button title="Confirm sign out everywhere" variant="danger" loading={busy === 'logout'} disabled={busy !== null} onPress={signOutEverywhere} />
          <Button title="Keep my sessions" variant="outline" disabled={busy !== null} onPress={() => setConfirm(false)} /></>
          : <Button title="Sign out all devices" variant="outline" disabled={busy !== null} onPress={() => setConfirm(true)} />}
      </View>
      <View style={{ padding: 20, borderRadius: 18, gap: 14, backgroundColor: Colors.bgCard, borderWidth: 1, borderColor: Colors.border }}>
        <Text style={{ color: Colors.textPrimary, fontSize: 19, fontWeight: '700' }}>Delete your account</Text>
        <Text style={{ color: Colors.textSecondary, lineHeight: 22 }}>Verify your password or email code to disable access and request permanent cleanup of live account data. Export your records first.</Text>
        <Button title="Account deletion options" variant="outline" disabled={busy !== null} onPress={() => router.push('/profile/delete')} />
      </View>
      {!!message && <Text accessibilityLiveRegion="polite" style={{ color: Colors.textPrimary, lineHeight: 22 }}>{message}</Text>}
    </ScrollView>
  </SafeAreaView>;
}
