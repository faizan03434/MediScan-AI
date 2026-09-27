import React from 'react';
import { View, Text, ScrollView, TouchableOpacity } from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Colors } from '../../theme/colors';
import { SCAN_MODULES } from '../../types';

export default function ScanScreen() {
  const router = useRouter();

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: Colors.bgDark }}>
      <ScrollView contentContainerStyle={{ padding: 20 }} showsVerticalScrollIndicator={false}>
        <Text style={{ color: Colors.textPrimary, fontSize: 24, fontWeight: '800', marginBottom: 6 }}>
          Medical Scans
        </Text>
        <Text style={{ color: Colors.textSecondary, fontSize: 14, marginBottom: 24 }}>
          Select a scan type to start real-time detection
        </Text>

        {SCAN_MODULES.map((module) => (
          <TouchableOpacity
            key={module.id}
            onPress={() => router.push({ pathname: '/scan/[type]', params: { type: module.id } })}
            activeOpacity={0.8}
            style={{
              flexDirection: 'row',
              alignItems: 'center',
              backgroundColor: Colors.bgCard,
              borderRadius: 20,
              padding: 16,
              marginBottom: 12,
              borderWidth: 1,
              borderColor: Colors.border,
              gap: 14,
            }}
          >
            <View style={{
              width: 56, height: 56, borderRadius: 28,
              backgroundColor: `${module.color}20`,
              alignItems: 'center', justifyContent: 'center',
              borderWidth: 1.5, borderColor: `${module.color}50`,
              flexShrink: 0,
            }}>
              <Text style={{ fontSize: 26 }}>{module.icon}</Text>
            </View>

            <View style={{ flex: 1 }}>
              <Text style={{ color: Colors.textPrimary, fontSize: 16, fontWeight: '700' }}>
                {module.title}
              </Text>
              <Text style={{ color: Colors.textMuted, fontSize: 13, marginTop: 2 }} numberOfLines={2}>
                {module.description}
              </Text>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4, marginTop: 6 }}>
                <Text style={{ color: Colors.textMuted, fontSize: 11 }}>📍</Text>
                <Text style={{ color: Colors.textMuted, fontSize: 11 }}>{module.targetArea}</Text>
              </View>
            </View>

            <Text style={{ color: module.color, fontSize: 20 }}>›</Text>
          </TouchableOpacity>
        ))}

        <Text style={{
          color: Colors.textMuted, fontSize: 12, textAlign: 'center',
          marginTop: 12, lineHeight: 18,
        }}>
          🔒 All scans are encrypted and stored securely.{'\n'}
          AI results are screening tools — always consult a doctor.
        </Text>
      </ScrollView>
    </SafeAreaView>
  );
}
