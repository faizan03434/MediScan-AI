import React from 'react';
import { View, Text, ScrollView, TouchableOpacity, Alert } from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useQuery } from '@tanstack/react-query';
import scanService from '../../services/scanService';
import useAuthStore from '../../store/authStore';
import Card from '../../components/common/Card';
import Button from '../../components/common/Button';
import { Colors } from '../../theme/colors';
import { SCAN_MODULES } from '../../types';

export default function ProfileScreen() {
  const router = useRouter();
  const { user, logout, refreshToken } = useAuthStore();

  const { data: recentScans } = useQuery({
    queryKey: ['recentScans'],
    queryFn: () => scanService.getRecentScans(10),
  });

  const handleLogout = () => {
    Alert.alert(
      'Logout',
      'Are you sure you want to log out?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Logout',
          style: 'destructive',
          onPress: async () => {
            await logout();
            router.replace('/(auth)/login');
          },
        },
      ]
    );
  };

  const scanCountByType = SCAN_MODULES.map(mod => ({
    ...mod,
    count: recentScans?.filter(s => s.scanType === mod.id).length ?? 0,
  }));

  const age = user?.dateOfBirth
    ? Math.floor((Date.now() - new Date(user.dateOfBirth).getTime()) / (1000 * 60 * 60 * 24 * 365.25))
    : null;

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: Colors.bgDark }}>
      <ScrollView contentContainerStyle={{ paddingBottom: 32 }} showsVerticalScrollIndicator={false}>
        {/* Profile header */}
        <View style={{
          alignItems: 'center',
          paddingVertical: 28,
          paddingHorizontal: 20,
          borderBottomWidth: 1,
          borderBottomColor: Colors.border,
        }}>
          <View style={{
            width: 80, height: 80, borderRadius: 40,
            backgroundColor: `${Colors.primary}30`,
            alignItems: 'center', justifyContent: 'center',
            borderWidth: 3, borderColor: Colors.primary,
            marginBottom: 12,
          }}>
            <Text style={{ fontSize: 36 }}>👤</Text>
          </View>
          <Text style={{ color: Colors.textPrimary, fontSize: 22, fontWeight: '800' }}>
            {user?.fullName ?? 'User'}
          </Text>
          <Text style={{ color: Colors.textSecondary, fontSize: 14, marginTop: 4 }}>
            {user?.email}
          </Text>
          <View style={{
            marginTop: 8,
            backgroundColor: `${Colors.primary}20`, borderRadius: 20,
            paddingHorizontal: 14, paddingVertical: 4,
          }}>
            <Text style={{ color: Colors.primary, fontSize: 12, fontWeight: '700' }}>
              {user?.role ?? 'User'}
            </Text>
          </View>
        </View>

        {/* Health info */}
        <View style={{ paddingHorizontal: 20, marginTop: 20 }}>
          <Text style={{ color: Colors.textPrimary, fontSize: 17, fontWeight: '700', marginBottom: 12 }}>
            Health Profile
          </Text>
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 10 }}>
            {[
              { label: 'Age',        value: age ? `${age} yrs` : '—', icon: '🎂' },
              { label: 'Gender',     value: user?.gender ?? '—',       icon: '⚧' },
              { label: 'Blood Type', value: user?.bloodGroup ?? '—',   icon: '🩸' },
              { label: 'Weight',     value: user?.weightKg ? `${user.weightKg} kg` : '—', icon: '⚖️' },
              { label: 'Height',     value: user?.heightCm ? `${user.heightCm} cm` : '—', icon: '📏' },
            ].map((item) => (
              <View key={item.label} style={{
                flex: 1, minWidth: '45%',
                backgroundColor: Colors.bgCard,
                borderRadius: 14, padding: 12,
                borderWidth: 1, borderColor: Colors.border,
              }}>
                <Text style={{ fontSize: 18 }}>{item.icon}</Text>
                <Text style={{ color: Colors.textPrimary, fontWeight: '700', fontSize: 15, marginTop: 4 }}>
                  {item.value}
                </Text>
                <Text style={{ color: Colors.textMuted, fontSize: 11 }}>{item.label}</Text>
              </View>
            ))}
          </View>

          <Button
            title="Edit Profile"
            variant="outline"
            onPress={() => Alert.alert('Edit Profile', 'Coming in next update')}
            fullWidth
            style={{ marginTop: 14 }}
          />
        </View>

        {/* Scan stats */}
        <View style={{ paddingHorizontal: 20, marginTop: 24 }}>
          <Text style={{ color: Colors.textPrimary, fontSize: 17, fontWeight: '700', marginBottom: 12 }}>
            My Scan Activity
          </Text>
          {scanCountByType.map(mod => (
            <View key={mod.id} style={{
              flexDirection: 'row', alignItems: 'center',
              paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: Colors.border,
              gap: 12,
            }}>
              <Text style={{ fontSize: 18, width: 28 }}>{mod.icon}</Text>
              <Text style={{ flex: 1, color: Colors.textSecondary, fontSize: 14 }}>{mod.title}</Text>
              <View style={{
                backgroundColor: mod.count > 0 ? `${mod.color}20` : Colors.bgInput,
                borderRadius: 10, paddingHorizontal: 10, paddingVertical: 3,
              }}>
                <Text style={{ color: mod.count > 0 ? mod.color : Colors.textMuted, fontWeight: '700', fontSize: 13 }}>
                  {mod.count}
                </Text>
              </View>
            </View>
          ))}
        </View>

        {/* Settings & Logout */}
        <View style={{ paddingHorizontal: 20, marginTop: 28, gap: 10 }}>
          {[
            { label: '👨‍⚕️ Doctor Portal', action: () => router.push('/doctor') },
            { label: '🔐 Doctor Access Requests', action: () => router.push('/doctor/consents') },
            { label: '🔔 Notifications', action: () => Alert.alert('Coming Soon') },
            { label: '🔒 Privacy & Data', action: () => Alert.alert('Coming Soon') },
            { label: '📋 HIPAA Consent',  action: () => Alert.alert('Coming Soon') },
            { label: '❓ Help & Support', action: () => Alert.alert('Coming Soon') },
          ].map((item) => (
            <TouchableOpacity
              key={item.label}
              onPress={item.action}
              style={{
                backgroundColor: Colors.bgCard,
                borderRadius: 14, padding: 16,
                flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
                borderWidth: 1, borderColor: Colors.border,
              }}
            >
              <Text style={{ color: Colors.textSecondary, fontSize: 14 }}>{item.label}</Text>
              <Text style={{ color: Colors.textMuted }}>›</Text>
            </TouchableOpacity>
          ))}

          <Button
            title="Logout"
            variant="danger"
            onPress={handleLogout}
            fullWidth
            style={{ marginTop: 8 }}
          />
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}
