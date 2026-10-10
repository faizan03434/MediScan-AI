import { createElement, useEffect, useRef, useState } from 'react';
import { Text, View } from 'react-native';
import { useRouter } from 'expo-router';
import Button from '../common/Button';
import authService from '../../services/authService';
import useAuthStore from '../../store/authStore';
import { Colors } from '../../theme/colors';
import { errorMessage } from '../../utils/errorMessage';

interface GoogleId { initialize(options: { client_id: string; callback: (response: { credential: string }) => void; auto_select: boolean }): void; renderButton(element: HTMLElement, options: { theme: string; size: string; text: string; width: number }): void }
declare global { interface Window { google?: { accounts: { id: GoogleId } } } }

export default function GoogleSignInButton({ link = false }: { link?: boolean }) {
  const router = useRouter();
  const acceptAuth = useAuthStore(s => s.acceptAuth);
  const host = useRef<HTMLDivElement>(null);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const clientId = process.env.EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID;
  useEffect(() => {
    if (!clientId) return;
    let active = true;
    const render = () => {
      if (!active || !host.current || !window.google) return;
      window.google.accounts.id.initialize({ client_id: clientId, auto_select: false, callback: async ({ credential }) => {
        if (!active) return;
        setBusy(true); setMessage('');
        try { const account = await authService.googleSignIn(credential, link); if (account) { acceptAuth(account); router.replace('/(tabs)/home'); } else setMessage('Google account linked successfully.'); }
        catch (e) { if (active) setMessage(errorMessage(e)); } finally { if (active) setBusy(false); }
      } });
      host.current.replaceChildren();
      window.google.accounts.id.renderButton(host.current, { theme: 'outline', size: 'large', text: 'continue_with', width: Math.min(350, host.current.clientWidth || 300) });
    };
    let script = document.getElementById('mediscan-google-identity') as HTMLScriptElement | null;
    if (window.google) render();
    else {
      if (!script) { script = document.createElement('script'); script.id = 'mediscan-google-identity'; script.src = 'https://accounts.google.com/gsi/client'; script.async = true; document.head.appendChild(script); }
      script.addEventListener('load', render);
    }
    const fail = () => setMessage('Google could not load. Check your connection and reload.');
    script?.addEventListener('error', fail);
    return () => { active = false; script?.removeEventListener('load', render); script?.removeEventListener('error', fail); };
  }, [clientId, link, acceptAuth, router]);
  return <View style={{ gap: 10 }}>{clientId ? createElement('div', { ref: host, style: { minHeight: 44, width: '100%', pointerEvents: busy ? 'none' : 'auto' } }) : <Button title={link ? 'Link Google account' : 'Continue with Google'} variant="outline" fullWidth onPress={() => setMessage('Google sign-in is not available yet. Please use email sign-in.')} />}{busy && <Text style={{ color: Colors.textMuted }}>Signing in…</Text>}{!!message && <Text accessibilityRole="alert" style={{ color: Colors.textSecondary, lineHeight: 20, fontSize: 13 }}>{message}</Text>}</View>;
}
