import { useEffect } from 'react';
import { View, ActivityIndicator } from 'react-native';
import { useRouter } from 'expo-router';
import useAuthStore from '../store/authStore';
import { AppStorage } from '../utils/storage';
import { Colors } from '../theme/colors';

/**
 * Entry point — determines where to navigate based on:
 * 1. Onboarding complete?  → No  → /onboarding
 * 2. HIPAA consent given?  → No  → /onboarding/consent
 * 3. Authenticated?        → Yes → /(tabs)/home
 *                          → No  → /(auth)/login
 */
export default function Index() {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuthStore();

  useEffect(() => {
    if (isLoading) return;

    (async () => {
      const onboardingDone = await AppStorage.isOnboardingComplete();
      if (!onboardingDone) {
        router.replace('/onboarding');
        return;
      }

      const hasConsent = await AppStorage.hasHipaaConsent();
      if (!hasConsent) {
        router.replace('/onboarding/consent');
        return;
      }

      if (isAuthenticated) {
        router.replace('/(tabs)/home');
      } else {
        router.replace('/(auth)/login');
      }
    })();
  }, [isAuthenticated, isLoading]);

  return (
    <View style={{ flex: 1, backgroundColor: Colors.bgDark, alignItems: 'center', justifyContent: 'center' }}>
      <ActivityIndicator size="large" color={Colors.primary} />
    </View>
  );
}
