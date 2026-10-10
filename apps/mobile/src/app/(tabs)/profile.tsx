import React, { useState } from 'react';
import { View, Text, ScrollView, TouchableOpacity } from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useQuery } from '@tanstack/react-query';
import scanService from '../../services/scanService';
import useAuthStore from '../../store/authStore';
import Button from '../../components/common/Button';
import { Colors } from '../../theme/colors';
import { SCAN_MODULES } from '../../types';

export default function ProfileScreen() {
  const router = useRouter();
  const { user, logout } = useAuthStore();
  const [confirmLogout, setConfirmLogout] = useState(false);

  const { data: recentScans } = useQuery({
    queryKey: ['recentScans', 10],
    queryFn: () => scanService.getRecentScans(10),
  });

  const handleLogout = async () => { await logout(); router.replace('/(auth)/login'); };

  const scanCountByType = SCAN_MODULES.map(mod => ({
    ...mod,
    count: recentScans?.filter(s => s.scanType === mod.id).length ?? 0,
  }));

  const age = user?.dateOfBirth
    ? Math.floor((Date.now() - new Date(user.dateOfBirth).getTime()) / (1000 * 60 * 60 * 24 * 365.25))
    : null;

  return (
    <SafeAreaView edges={["left", "right"]} style={{ flex: 1, backgroundColor: Colors.bgDark }}>
      <ScrollView contentContainerStyle={{ paddingBottom: 32, width: '100%', maxWidth: 800, alignSelf: 'center' }} showsVerticalScrollIndicator={false}>
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
            onPress={() => router.push('/profile/edit')}
            fullWidth
            style={{ marginTop: 14 }}
          />
        </View>

        {/* Scan stats */}
        <View style={{ paddingHorizontal: 20, marginTop: 24 }}>
          <Text style={{ color: Colors.textPrimary, fontSize: 17, fontWeight: '700', marginBottom: 12 }}>
            Recent Scan Activity (last 10)
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
            ...(user?.role === 'Doctor' || user?.role === 'Admin' ? [{ label: '👨‍⚕️ Doctor Portal', action: () => router.push('/doctor') }] : []),
            { label: '🔐 Doctor Access Requests', action: () => router.push('/doctor/consents') },
            { label: '📋 Account Activity', action: () => router.push('/profile/activity') },
            { label: '🔒 Privacy & Data', action: () => router.push({ pathname: '/information/[topic]', params: { topic: 'privacy' } }) },
            { label: '❓ Help & Support', action: () => router.push({ pathname: '/information/[topic]', params: { topic: 'help' } }) },
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

          {confirmLogout && <View style={{ gap: 12, padding: 16, backgroundColor: Colors.white, borderRadius: 14 }}><Text style={{ color: Colors.textSecondary }}>Sign out of this device?</Text><Button title="Confirm sign out" onPress={handleLogout} fullWidth /><Button title="Keep me signed in" variant="outline" onPress={() => setConfirmLogout(false)} fullWidth /></View>}
          <Button
            title="Logout"
            variant="danger"
            onPress={() => setConfirmLogout(true)}
            fullWidth
            style={{ marginTop: 8 }}
          />
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}
