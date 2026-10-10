import React from 'react';
import {
  View,
  Text,
  ScrollView,
  RefreshControl,
  TouchableOpacity,
} from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useQuery } from '@tanstack/react-query';
import { LinearGradient } from 'expo-linear-gradient';
import useAuthStore from '../../store/authStore';
import scanService from '../../services/scanService';
import ScanModuleCard from '../../components/dashboard/ScanModuleCard';
import Card from '../../components/common/Card';
import { Colors } from '../../theme/colors';
import { SCAN_MODULES, type ScanType } from '../../types';
import { format } from 'date-fns';

export default function HomeScreen() {
  const router = useRouter();
  const { user } = useAuthStore();

  const { data: recentScans, refetch, isRefetching } = useQuery({
    queryKey: ['recentScans', 5],
    queryFn: () => scanService.getRecentScans(5),
    staleTime: 1000 * 60 * 2, // 2 min
  });

  const lastScanMap = recentScans?.reduce((acc, scan) => {
    if (!acc[scan.scanType]) {
      acc[scan.scanType] = format(new Date(scan.createdAt), 'MMM d');
    }
    return acc;
  }, {} as Partial<Record<ScanType, string>>) ?? {} as Partial<Record<ScanType, string>>;

  const greeting = () => {
    const h = new Date().getHours();
    if (h < 12) return 'Good Morning';
    if (h < 18) return 'Good Afternoon';
    return 'Good Evening';
  };

  return (
    <SafeAreaView edges={["left", "right"]} style={{ flex: 1, backgroundColor: Colors.bgDark }}>
      <ScrollView
        contentContainerStyle={{ paddingBottom: 24, width: '100%', maxWidth: 1000, alignSelf: 'center' }}
        refreshControl={
          <RefreshControl
            refreshing={isRefetching}
            onRefresh={refetch}
            tintColor={Colors.primary}
          />
        }
        showsVerticalScrollIndicator={false}
      >
        <View style={{ margin: 16, padding: 14, backgroundColor: `${Colors.warning}15`, borderRadius: 12 }}>
          <Text style={{ color: Colors.warning, fontWeight: '700' }}>Research preview</Text>
          <Text style={{ color: Colors.textSecondary, marginTop: 4 }}>{SCAN_MODULES.length} photo workflows are available. Clinical detection, healing assessment and prescription verification are not yet validated.</Text>
        </View>
        {/* Header */}
        <LinearGradient
          colors={['#FFFFFF', '#F6F7F9']}
          style={{ paddingHorizontal: 20, paddingTop: 16, paddingBottom: 28, borderBottomLeftRadius: 28, borderBottomRightRadius: 28 }}
        >
          <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <View>
              <Text style={{ color: Colors.textSecondary, fontSize: 14 }}>
                {greeting()},
              </Text>
              <Text style={{ color: Colors.textPrimary, fontSize: 22, fontWeight: '800', marginTop: 2 }}>
                {user?.fullName?.split(' ')[0] ?? 'User'} 👋
              </Text>
            </View>
            <TouchableOpacity
              onPress={() => router.push('/(tabs)/profile')}
              style={{
                width: 44, height: 44, borderRadius: 22,
                backgroundColor: `${Colors.primary}30`,
                alignItems: 'center', justifyContent: 'center',
                borderWidth: 2, borderColor: `${Colors.primary}60`,
              }}
            >
              <Text style={{ fontSize: 20 }}>👤</Text>
            </TouchableOpacity>
          </View>

          {/* Health summary strip */}
          <View style={{
            flexDirection: 'row',
            marginTop: 20,
            gap: 10,
          }}>
            {[
              { label: 'Recent Scans', value: recentScans?.length ?? 0, icon: '📷' },
              { label: 'Recent this month', value: recentScans?.filter(s => new Date(s.createdAt).getMonth() === new Date().getMonth() && new Date(s.createdAt).getFullYear() === new Date().getFullYear()).length ?? 0, icon: '📅' },
            ].map((stat) => (
              <View key={stat.label} style={{
                flex: 1,
                backgroundColor: Colors.white,
                borderRadius: 14,
                padding: 12,
              }}>
                <Text style={{ fontSize: 18 }}>{stat.icon}</Text>
                <Text style={{ color: Colors.textPrimary, fontSize: 20, fontWeight: '800', marginTop: 4 }}>
                  {recentScans ? stat.value : '—'}
                </Text>
                <Text style={{ color: Colors.textMuted, fontSize: 12 }}>{stat.label}</Text>
              </View>
            ))}
          </View>
        </LinearGradient>

        {/* Scan Modules grid */}
        <View style={{ paddingHorizontal: 20, marginTop: 24 }}>
          <Text style={{ color: Colors.textPrimary, fontSize: 18, fontWeight: '700', marginBottom: 14 }}>
            Health Scans
          </Text>
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 12 }}>
            {SCAN_MODULES.map((module) => (
              <ScanModuleCard
                key={module.id}
                module={module}
                lastScan={lastScanMap[module.id]}
                onPress={() =>
                  router.push({
                    pathname: '/scan/[type]',
                    params: { type: module.id },
                  })
                }
              />
            ))}
          </View>
        </View>

        {/* Recent scan results */}
        {recentScans && recentScans.length > 0 && (
          <View style={{ paddingHorizontal: 20, marginTop: 28 }}>
            <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
              <Text style={{ color: Colors.textPrimary, fontSize: 18, fontWeight: '700' }}>
                Recent Results
              </Text>
              <TouchableOpacity onPress={() => router.push('/(tabs)/history')}>
                <Text style={{ color: Colors.primary, fontSize: 13, fontWeight: '600' }}>
                  View All →
                </Text>
              </TouchableOpacity>
            </View>
            {recentScans.slice(0, 3).map((scan) => {
              const mod = SCAN_MODULES.find(m => m.id === scan.scanType);
              return (
                <Card key={scan.id} padding={14} style={{ marginBottom: 10 }}>
                  <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
                    <View style={{
                      width: 44, height: 44, borderRadius: 22,
                      backgroundColor: `${mod?.color ?? Colors.primary}20`,
                      alignItems: 'center', justifyContent: 'center',
                    }}>
                      <Text style={{ fontSize: 20 }}>{mod?.icon ?? '🔍'}</Text>
                    </View>
                    <View style={{ flex: 1 }}>
                      <Text style={{ color: Colors.textPrimary, fontWeight: '700', fontSize: 14 }}>
                        {mod?.title ?? scan.scanType}
                      </Text>
                      <Text style={{ color: Colors.textMuted, fontSize: 12, marginTop: 2 }} numberOfLines={1}>
                        {scan.detectionResult ?? 'Processing...'}
                      </Text>
                    </View>
                    <View>
                      <Text style={{ color: Colors.textMuted, fontSize: 11 }}>
                        {format(new Date(scan.createdAt), 'MMM d')}
                      </Text>
                      <View style={{
                        marginTop: 4,
                        backgroundColor: scan.status === 'Completed' ? `${Colors.success}20` : `${Colors.warning}20`,
                        borderRadius: 6, paddingHorizontal: 6, paddingVertical: 2,
                      }}>
                        <Text style={{
                          fontSize: 10, fontWeight: '600',
                          color: scan.status === 'Completed' ? Colors.success : Colors.warning,
                        }}>
                          {scan.status}
                        </Text>
                      </View>
                    </View>
                  </View>
                </Card>
              );
            })}
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}
