import { useState } from 'react';
import { Text, TouchableOpacity, View } from 'react-native';
import { useRouter } from 'expo-router';
import AuthShell from '../../components/auth/AuthShell';
import GoogleSignInButton from '../../components/auth/GoogleSignInButton';
import Input from '../../components/common/Input';
import Button from '../../components/common/Button';
import useAuthStore from '../../store/authStore';
import { Colors } from '../../theme/colors';
import { errorMessage } from '../../utils/errorMessage';

export default function LoginScreen() {
  const router = useRouter();
  const login = useAuthStore(s => s.login);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const submit = async () => {
    setBusy(true); setError('');
    try {
      if (!email.trim() || !password) throw new Error('Enter your email and password.');
      await login({ email: email.trim(), password });
      setPassword(''); router.replace('/(tabs)/home');
    } catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
  };
  return <AuthShell title="Welcome back" subtitle="Your records, photos and progress in one place.">
    <Input label="Email address" value={email} onChangeText={setEmail} keyboardType="email-address" autoCapitalize="none" autoComplete="email" placeholder="you@example.com" />
    <Input label="Password" value={password} onChangeText={setPassword} isPassword autoComplete="current-password" onSubmitEditing={submit} placeholder="Enter your password" />
    <TouchableOpacity onPress={() => router.push('/(auth)/forgot-password')} style={{ alignSelf: 'flex-end', marginBottom: 20 }}><Text style={{ color: Colors.primary, fontWeight: '600', fontSize: 13 }}>Forgot password?</Text></TouchableOpacity>
    {!!error && <Text accessibilityRole="alert" style={{ color: Colors.danger, marginBottom: 16, lineHeight: 21 }}>{error}</Text>}
    <Button title="Sign in" fullWidth loading={busy} onPress={submit} />
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12, marginVertical: 22 }}><View style={{ flex: 1, height: 1, backgroundColor: Colors.border }} /><Text style={{ color: Colors.textMuted, fontSize: 12 }}>or</Text><View style={{ flex: 1, height: 1, backgroundColor: Colors.border }} /></View>
    <GoogleSignInButton />
    <TouchableOpacity onPress={() => router.push('/(auth)/register')} style={{ marginTop: 24 }}><Text style={{ color: Colors.textSecondary, textAlign: 'center' }}>New here? <Text style={{ color: Colors.primary, fontWeight: '700' }}>Create an account</Text></Text></TouchableOpacity>
  </AuthShell>;
}
