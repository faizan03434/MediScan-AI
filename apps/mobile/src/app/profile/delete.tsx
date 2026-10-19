import React, { useState } from 'react';
import { ScrollView, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { useQueryClient } from '@tanstack/react-query';
import { isAxiosError } from 'axios';
import Button from '../../components/common/Button';
import { requestAccountDeletion, sendDeletionCode } from '../../services/accountDeletionService';
import useAuthStore from '../../store/authStore';
import { Colors } from '../../theme/colors';

export default function DeleteAccountScreen() {
  const router = useRouter(); const cache = useQueryClient();
  const [password, setPassword] = useState(''); const [code, setCode] = useState('');
  const [confirmation, setConfirmation] = useState(''); const [challenge, setChallenge] = useState('');
  const [emailMode, setEmailMode] = useState(false); const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState(''); const [resendAt, setResendAt] = useState(0);
  function errorMessage(error: unknown) {
    return isAxiosError(error) ? error.response?.data?.message || 'Request could not be confirmed. If your account is disabled, check deletion status or contact support.'
      : error instanceof Error ? error.message : 'Please retry.';
  }
  async function sendCode() {
    setBusy(true); setMessage('');
    try { const result = await sendDeletionCode(); setChallenge(result.challengeId); setCode('');
      setResendAt(Date.now() + result.resendAfterSeconds * 1000); setMessage('Code sent. It expires in 10 minutes.'); }
    catch (error) { setMessage(errorMessage(error)); } finally { setBusy(false); }
  }
  async function remove() {
    setBusy(true); setMessage('');
    try {
      await requestAccountDeletion({ confirmation, ...(emailMode ? { challengeId: challenge, code } : { password }) });
      setPassword(''); setCode(''); cache.clear();
      await useAuthStore.getState().logout(); router.replace('/deletion-status');
    } catch (error) { setMessage(errorMessage(error)); } finally { setBusy(false); }
  }
  const input = { color: Colors.textPrimary, backgroundColor: Colors.bgInput, borderColor: Colors.border,
    borderWidth: 1, borderRadius: 12, padding: 14 };
  return <SafeAreaView style={{ flex: 1, backgroundColor: Colors.bgDark }}>
    <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={{ padding: 20, gap: 18, maxWidth: 650, width: '100%', alignSelf: 'center' }}>
      <Button title="Back" variant="ghost" disabled={busy} onPress={() => router.back()} />
      <Text accessibilityRole="header" style={{ color: Colors.textPrimary, fontSize: 26, fontWeight: '800' }}>Delete your account</Text>
      <Text style={{ color: Colors.textSecondary, lineHeight: 23 }}>Export any records you want to keep first. After verification, your account will be disabled on all devices and doctor access will be revoked. Live account records and unshared photos will be queued for permanent removal. This cannot be undone.</Text>
      <Text style={{ color: Colors.textSecondary, lineHeight: 23 }}>Cleanup starts after a short delay and retries if a service is unavailable. Backups, storage versions and copies you shared elsewhere follow separate retention policies; this action does not erase those copies.</Text>
      <Button title={emailMode ? 'Use my password instead' : 'Use an email code instead'} variant="outline" disabled={busy} onPress={() => {
        setEmailMode(!emailMode); setPassword(''); setCode(''); setMessage('');
      }} />
      {emailMode ? <View style={{ gap: 12 }}>
        <Button title="Send verification code" variant="outline" loading={busy} disabled={busy} onPress={() => {
          if (Date.now() < resendAt) { setMessage('Wait 60 seconds before requesting another code.'); return; } void sendCode();
        }} />
        <TextInput accessibilityLabel="Deletion verification code" placeholder="Six-digit email code" placeholderTextColor={Colors.textMuted}
          keyboardType="number-pad" maxLength={6} value={code} onChangeText={setCode} editable={!busy} style={input} />
      </View> : <TextInput accessibilityLabel="Current password" placeholder="Current password" placeholderTextColor={Colors.textMuted}
        secureTextEntry autoCapitalize="none" autoCorrect={false} value={password} onChangeText={setPassword} editable={!busy} maxLength={100} style={input} />}
      <TextInput accessibilityLabel="Type DELETE to confirm" placeholder="Type DELETE to confirm" placeholderTextColor={Colors.textMuted}
        autoCapitalize="characters" autoCorrect={false} value={confirmation} onChangeText={setConfirmation} editable={!busy} maxLength={6} style={input} />
      <Button title="Permanently delete my account" variant="danger" loading={busy}
        disabled={busy || confirmation !== 'DELETE' || (emailMode ? !challenge || code.length !== 6 : !password)} onPress={remove} />
      {!!message && <Text accessibilityLiveRegion="polite" style={{ color: Colors.textPrimary, lineHeight: 23 }}>{message}</Text>}
    </ScrollView>
  </SafeAreaView>;
}
