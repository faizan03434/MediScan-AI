/**
 * Typed wrappers around expo-secure-store for persistent flags.
 * Used for onboarding completion, consent, etc.
 */
import * as SecureStore from 'expo-secure-store';

const KEYS = {
  ONBOARDING_COMPLETE: 'mediscan_onboarding_done',
  HIPAA_CONSENT:       'mediscan_hipaa_consent',
  CONSENT_DATE:        'mediscan_consent_date',
  PUSH_REGISTERED:     'mediscan_push_registered',
} as const;

export const AppStorage = {
  async isOnboardingComplete(): Promise<boolean> {
    const val = await SecureStore.getItemAsync(KEYS.ONBOARDING_COMPLETE);
    return val === 'true';
  },
  async setOnboardingComplete(): Promise<void> {
    await SecureStore.setItemAsync(KEYS.ONBOARDING_COMPLETE, 'true');
  },

  async hasHipaaConsent(): Promise<boolean> {
    const val = await SecureStore.getItemAsync(KEYS.HIPAA_CONSENT);
    return val === 'true';
  },
  async setHipaaConsent(): Promise<void> {
    await SecureStore.setItemAsync(KEYS.HIPAA_CONSENT, 'true');
    await SecureStore.setItemAsync(KEYS.CONSENT_DATE, new Date().toISOString());
  },
  async getConsentDate(): Promise<string | null> {
    return SecureStore.getItemAsync(KEYS.CONSENT_DATE);
  },

  async isPushRegistered(): Promise<boolean> {
    const val = await SecureStore.getItemAsync(KEYS.PUSH_REGISTERED);
    return val === 'true';
  },
  async setPushRegistered(): Promise<void> {
    await SecureStore.setItemAsync(KEYS.PUSH_REGISTERED, 'true');
  },

  async clearAll(): Promise<void> {
    await Promise.all(Object.values(KEYS).map(k => SecureStore.deleteItemAsync(k)));
  },
};
