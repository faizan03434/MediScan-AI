/**
 * Onboarding Step 2 — HIPAA Consent + Privacy
 * User must accept before accessing the app.
 */
import React, { useState } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity,
  Alert, ActivityIndicator,
} from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { Colors } from '../../theme/colors';
import { AppStorage } from '../../utils/storage';
import { registerForPushNotificationsAsync } from '../../hooks/useNotifications';

interface ConsentItem {
  id: string;
  icon: string;
  title: string;
  description: string;
  required: boolean;
}

const CONSENT_ITEMS: ConsentItem[] = [
  {
    id: 'screening_tool',
    icon: '⚕️',
    title: 'MediScan AI is a screening tool',
    description:
      'I understand that MediScan AI provides AI-assisted health screening results, NOT medical diagnoses. I will always consult a licensed doctor before making any health decisions.',
    required: true,
  },
  {
    id: 'data_storage',
    icon: '🔒',
    title: 'Local development data storage',
    description:
      'I consent to storing test photos and profile data on this development computer. This preview uses local storage and is not certified HIPAA compliant. I will use test data only.',
    required: true,
  },
  {
    id: 'audit_logs',
    icon: '📋',
    title: 'Audit logging',
    description:
      'I understand that implemented audit events are logged. Full read-access auditing, retention controls and user export still require implementation.',
    required: true,
  },
  {
    id: 'ai_processing',
    icon: '🤖',
    title: 'AI image processing',
    description:
      'I consent to uploading photos for a research preview. Clinical AI inference is disabled until models and their validation are reviewed. Images are retained locally under my account.',
    required: true,
  },
  {
    id: 'notifications',
    icon: '🔔',
    title: 'Health reminders (optional)',
    description:
      'I consent to receiving push notifications for scheduled rescan reminders. I can disable these at any time from my profile settings.',
    required: false,
  },
];

export default function ConsentScreen() {
  const router = useRouter();
  const [accepted, setAccepted] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(false);

  const allRequiredAccepted = CONSENT_ITEMS
    .filter(item => item.required)
    .every(item => accepted[item.id]);

  const toggle = (id: string) => {
    setAccepted(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const handleAcceptAll = async () => {
    if (!allRequiredAccepted) {
      Alert.alert(
        'Required Consent',
        'Please accept all required consent items (marked with *) to continue.',
      );
      return;
    }

    setLoading(true);
    try {
      // Save consent
      await AppStorage.setHipaaConsent();
      await AppStorage.setOnboardingComplete();

      // Register for push notifications if user opted in
      if (accepted['notifications']) {
        const status = await registerForPushNotificationsAsync();
        if (status === 'granted') {
          await AppStorage.setPushRegistered();
        }
      }

      // Navigate to registration
      router.replace('/(auth)/register');
    } catch {
      Alert.alert('Error', 'Something went wrong. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: Colors.bgDark }}>
      <ScrollView
        contentContainerStyle={{ padding: 20, paddingBottom: 120 }}
        showsVerticalScrollIndicator={false}
      >
        {/* Header */}
        <View style={{ alignItems: 'center', marginBottom: 28 }}>
          <View style={{
            width: 72, height: 72, borderRadius: 36,
            backgroundColor: `${Colors.primary}20`,
            alignItems: 'center', justifyContent: 'center',
            borderWidth: 2, borderColor: `${Colors.primary}50`,
            marginBottom: 14,
          }}>
            <Text style={{ fontSize: 34 }}>🔐</Text>
          </View>
          <Text style={{ color: Colors.textPrimary, fontSize: 24, fontWeight: '800', textAlign: 'center' }}>
            Your Privacy & Consent
          </Text>
          <Text style={{ color: Colors.textSecondary, fontSize: 14, textAlign: 'center', marginTop: 8, lineHeight: 20 }}>
            Please read and accept the following before using MediScan AI.{'\n'}
            Items marked <Text style={{ color: Colors.danger }}>*</Text> are required.
          </Text>
        </View>

        {/* Consent items */}
        {CONSENT_ITEMS.map((item) => {
          const isChecked = !!accepted[item.id];
          return (
            <TouchableOpacity
              key={item.id}
              onPress={() => toggle(item.id)}
              activeOpacity={0.85}
              style={{
                flexDirection: 'row',
                backgroundColor: isChecked ? `${Colors.primary}10` : Colors.bgCard,
                borderRadius: 16, padding: 16, marginBottom: 10,
                borderWidth: 1.5,
                borderColor: isChecked ? `${Colors.primary}60` : Colors.border,
                gap: 12,
              }}
            >
              {/* Checkbox */}
              <View style={{
                width: 26, height: 26, borderRadius: 8,
                borderWidth: 2,
                borderColor: isChecked ? Colors.primary : Colors.border,
                backgroundColor: isChecked ? Colors.primary : 'transparent',
                alignItems: 'center', justifyContent: 'center',
                flexShrink: 0, marginTop: 1,
              }}>
                {isChecked && (
                  <Text style={{ color: Colors.white, fontSize: 14, fontWeight: '800' }}>✓</Text>
                )}
              </View>

              <View style={{ flex: 1 }}>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                  <Text style={{ fontSize: 16 }}>{item.icon}</Text>
                  <Text style={{ color: Colors.textPrimary, fontWeight: '700', fontSize: 14, flex: 1 }}>
                    {item.title}
                    {item.required && (
                      <Text style={{ color: Colors.danger }}> *</Text>
                    )}
                  </Text>
                </View>
                <Text style={{ color: Colors.textSecondary, fontSize: 13, lineHeight: 19 }}>
                  {item.description}
                </Text>
              </View>
            </TouchableOpacity>
          );
        })}

        {/* HIPAA badge */}
        <View style={{
          flexDirection: 'row', alignItems: 'center', gap: 12,
          backgroundColor: `${Colors.success}10`,
          borderRadius: 14, padding: 14, marginTop: 8,
          borderWidth: 1, borderColor: `${Colors.success}30`,
        }}>
          <Text style={{ fontSize: 24 }}>🛡️</Text>
          <View style={{ flex: 1 }}>
            <Text style={{ color: Colors.success, fontWeight: '700', fontSize: 13 }}>
              Development preview
            </Text>
            <Text style={{ color: Colors.textMuted, fontSize: 12, marginTop: 2 }}>
              Local test data · Clinical validation and compliance pending
            </Text>
          </View>
        </View>

        {/* Links */}
        <View style={{ flexDirection: 'row', justifyContent: 'center', gap: 20, marginTop: 16 }}>
          <TouchableOpacity>
            <Text style={{ color: Colors.primary, fontSize: 13 }}>Privacy Policy</Text>
          </TouchableOpacity>
          <Text style={{ color: Colors.border }}>·</Text>
          <TouchableOpacity>
            <Text style={{ color: Colors.primary, fontSize: 13 }}>Terms of Service</Text>
          </TouchableOpacity>
          <Text style={{ color: Colors.border }}>·</Text>
          <TouchableOpacity>
            <Text style={{ color: Colors.primary, fontSize: 13 }}>Development Notice</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>

      {/* Fixed bottom button */}
      <View style={{
        position: 'absolute', bottom: 0, left: 0, right: 0,
        backgroundColor: Colors.bgDark,
        paddingHorizontal: 20, paddingTop: 12, paddingBottom: 32,
        borderTopWidth: 1, borderTopColor: Colors.border,
      }}>
        <TouchableOpacity onPress={handleAcceptAll} disabled={loading || !allRequiredAccepted}>
          <LinearGradient
            colors={allRequiredAccepted
              ? [Colors.primary, Colors.primaryDark]
              : [Colors.border, Colors.border]}
            start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }}
            style={{
              borderRadius: 16, paddingVertical: 16,
              alignItems: 'center', justifyContent: 'center',
              flexDirection: 'row', gap: 8,
            }}
          >
            {loading ? (
              <ActivityIndicator color={Colors.white} />
            ) : (
              <>
                <Text style={{
                  color: allRequiredAccepted ? Colors.white : Colors.textMuted,
                  fontWeight: '700', fontSize: 16,
                }}>
                  Accept & Create Account
                </Text>
                {allRequiredAccepted && (
                  <Text style={{ color: Colors.white, fontSize: 16 }}>→</Text>
                )}
              </>
            )}
          </LinearGradient>
        </TouchableOpacity>

        <Text style={{
          color: Colors.textMuted, fontSize: 11, textAlign: 'center', marginTop: 8,
        }}>
          You can withdraw consent and delete your data at any time from Profile settings.
        </Text>
      </View>
    </SafeAreaView>
  );
}
