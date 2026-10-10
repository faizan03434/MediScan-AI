import { useState } from 'react';
import { Platform, Text, View } from 'react-native';
import Constants from 'expo-constants';
import { useRouter } from 'expo-router';
import Button from '../common/Button';
import authService from '../../services/authService';
import useAuthStore from '../../store/authStore';
import { Colors } from '../../theme/colors';
import { errorMessage } from '../../utils/errorMessage';

export default function GoogleSignInButton({ link = false }: { link?: boolean }) {
  const router = useRouter();
  const acceptAuth = useAuthStore(s => s.acceptAuth);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const signIn = async () => {
    setMessage(''); setBusy(true);
    try {
      const webClientId = process.env.EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID;
      const iosClientId = process.env.EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID;
      if (!webClientId || Platform.OS === 'ios' && !iosClientId) throw new Error('Google sign-in is not available yet. Please use email sign-in.');
      if (Constants.executionEnvironment === 'storeClient') throw new Error('Google sign-in requires a MediScan development build. You can use email sign-in in Expo Go.');
      // Load only after checking Expo Go: its native module is unavailable in Expo Go.
      const { GoogleSignin, isSuccessResponse } = await import('@react-native-google-signin/google-signin');
      GoogleSignin.configure({ webClientId, iosClientId });
      if (Platform.OS === 'android') await GoogleSignin.hasPlayServices({ showPlayServicesUpdateDialog: true });
      const result = await GoogleSignin.signIn();
      if (!isSuccessResponse(result)) return;
      if (!result.data.idToken) throw new Error('Google returned no identity token. Check the Web client ID.');
      const account = await authService.googleSignIn(result.data.idToken, link);
      if (account) { acceptAuth(account); router.replace('/(tabs)/home'); }
      else setMessage('Google account linked successfully.');
    } catch (e) { setMessage(errorMessage(e)); } finally { setBusy(false); }
  };
  return <View style={{ gap: 10 }}><Button title={link ? 'Link Google account' : 'Continue with Google'} variant="outline" fullWidth loading={busy} onPress={signIn} />{!!message && <Text accessibilityRole="alert" style={{ color: Colors.textSecondary, lineHeight: 20, fontSize: 13 }}>{message}</Text>}</View>;
}
