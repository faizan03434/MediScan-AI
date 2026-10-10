import { useEffect, useState } from 'react';
import { Text, TouchableOpacity, View } from 'react-native';
import { useRouter } from 'expo-router';
import AuthShell from './AuthShell';
import Input from '../common/Input';
import Button from '../common/Button';
import authService, { OtpChallenge } from '../../services/authService';
import useAuthStore from '../../store/authStore';
import { Colors } from '../../theme/colors';
import { errorMessage } from '../../utils/errorMessage';

export default function AccountEmailFlow({ registration }: { registration: boolean }) {
  const router = useRouter();
  const acceptAuth = useAuthStore(s => s.acceptAuth);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [code, setCode] = useState('');
  const [challenge, setChallenge] = useState<OtpChallenge | null>(null);
  const [resendAt, setResendAt] = useState(0);
  const [seconds, setSeconds] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [done, setDone] = useState(false);
  useEffect(() => {
    const tick = () => setSeconds(Math.max(0, Math.ceil((resendAt - Date.now()) / 1000)));
    tick(); const timer = setInterval(tick, 1000); return () => clearInterval(timer);
  }, [resendAt]);
  const checkPassword = () => {
    if (password.length < 8 || password.length > 100 || !/[A-Z]/.test(password) || !/[a-z]/.test(password) || !/[0-9]/.test(password)) throw new Error('Use 8–100 characters with an uppercase letter, lowercase letter and number.');
    if (password !== confirmPassword) throw new Error('Passwords do not match.');
  };
  const request = async () => {
    setBusy(true); setError('');
    try {
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) throw new Error('Enter a valid email address.');
      if (registration) { if (name.trim().length < 2) throw new Error('Enter your full name.'); checkPassword(); }
      const result = registration ? await authService.requestRegistration({ fullName: name.trim(), email: email.trim(), password, confirmPassword }) : await authService.requestPasswordReset(email.trim());
      setChallenge(result); setCode(''); setResendAt(Date.now() + result.resendAfterSeconds * 1000);
    } catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
  };
  const verify = async () => {
    if (!challenge) return;
    setBusy(true); setError('');
    try {
      if (!/^\d{6}$/.test(code)) throw new Error('Enter the six-digit code from your email.');
      const payload = { email: email.trim(), challengeId: challenge.challengeId, code };
      if (registration) { acceptAuth(await authService.verifyRegistration(payload)); setPassword(''); setConfirmPassword(''); router.replace('/(tabs)/home'); }
      else { checkPassword(); await authService.resetPassword({ ...payload, password, confirmPassword }); setPassword(''); setConfirmPassword(''); setDone(true); }
    } catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
  };
  return <AuthShell title={done ? 'Password updated' : challenge ? 'Check your email' : registration ? 'Create your account' : 'Forgot your password?'} subtitle={done ? 'You can now sign in with your new password.' : challenge ? `Enter the six-digit code for ${email}. Codes expire after 10 minutes.` : registration ? 'A simple place to keep your health photos and records.' : 'We’ll send a verification code to your registered email.'}>
    {done ? <Button fullWidth title="Back to sign in" onPress={() => router.replace('/(auth)/login')} /> : <>
      {!challenge && registration && <Input label="Full name" value={name} onChangeText={setName} autoComplete="name" />}
      {!challenge && <Input label="Email address" value={email} onChangeText={setEmail} keyboardType="email-address" autoCapitalize="none" autoComplete="email" />}
      {challenge && <><Text style={{ color: Colors.textSecondary, lineHeight: 21, marginBottom: 16 }}>{challenge.message}</Text><Input label="Verification code" value={code} onChangeText={v => setCode(v.replace(/\D/g, '').slice(0, 6))} maxLength={6} keyboardType="number-pad" autoComplete="one-time-code" textContentType="oneTimeCode" placeholder="000000" /></>}
      {(registration && !challenge || !registration && !!challenge) && <><Input label={registration ? 'Password' : 'New password'} value={password} onChangeText={setPassword} isPassword autoComplete="new-password" placeholder="8+ characters, uppercase, lowercase, number" /><Input label="Confirm password" value={confirmPassword} onChangeText={setConfirmPassword} isPassword /></>}
      {!!error && <Text accessibilityRole="alert" style={{ color: Colors.danger, lineHeight: 21, marginBottom: 16 }}>{error}</Text>}
      <Button fullWidth title={challenge ? registration ? 'Verify & create account' : 'Reset password' : 'Send verification code'} loading={busy} onPress={challenge ? verify : request} />
      {challenge && <View style={{ marginTop: 16, gap: 16 }}><TouchableOpacity disabled={busy || seconds > 0} onPress={request}><Text style={{ textAlign: 'center', color: seconds > 0 ? Colors.textMuted : Colors.primary }}>{seconds > 0 ? `Resend code in ${seconds}s` : 'Resend code'}</Text></TouchableOpacity><TouchableOpacity disabled={busy} onPress={() => { setChallenge(null); setError(''); }}><Text style={{ textAlign: 'center', color: Colors.primary }}>Change email</Text></TouchableOpacity></View>}
      <TouchableOpacity onPress={() => router.replace('/(auth)/login')} style={{ marginTop: 24 }}><Text style={{ textAlign: 'center', color: Colors.primary, fontWeight: '600' }}>Back to sign in</Text></TouchableOpacity>
    </>}
  </AuthShell>;
}
