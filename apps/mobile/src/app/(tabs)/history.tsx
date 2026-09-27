import React, { useState } from 'react';
import { View, Text, FlatList, TouchableOpacity, RefreshControl } from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useQuery } from '@tanstack/react-query';
import scanService from '../../services/scanService';
import Card from '../../components/common/Card';
import ConfidenceBadge from '../../components/common/ConfidenceBadge';
import { Colors } from '../../theme/colors';
import { SCAN_MODULES, type ScanType } from '../../types';
import { format } from 'date-fns';

const FILTER_OPTIONS: { label: string; value: ScanType | undefined }[] = [
  { label: 'All', value: undefined },
  { label: '🩸 Anemia', value: 'Anemia' },
  { label: '🦠 Skin', value: 'SkinDisease' },
  { label: '🦴 Posture', value: 'Posture' },
  { label: '👁️ Eye', value: 'EyeDisease' },
  { label: '🩹 Wound', value: 'Wound' },
  { label: '👅 Tongue', value: 'TongueDiagnosis' },
];

export default function HistoryScreen() {
  const router = useRouter();
  const [selectedType, setSelectedType] = useState<ScanType | undefined>();
  const [page, setPage] = useState(1);

  const { data, isLoading, refetch, isRefetching } = useQuery({
    queryKey: ['scanHistory', selectedType, page],
    queryFn: () => scanService.getHistory(selectedType, page, 15),
  });

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: Colors.bgDark }}>
      {/* Header */}
      <View style={{ paddingHorizontal: 20, paddingTop: 16, paddingBottom: 12 }}>
        <Text style={{ color: Colors.textPrimary, fontSize: 24, fontWeight: '800' }}>
          Scan History
        </Text>
        <Text style={{ color: Colors.textSecondary, fontSize: 13, marginTop: 2 }}>
          {data?.totalCount ?? 0} total scans
        </Text>
      </View>

      {/* Filter chips */}
      <FlatList
        data={FILTER_OPTIONS}
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={{ paddingHorizontal: 20, paddingBottom: 12, gap: 8 }}
        keyExtractor={(item) => item.label}
        renderItem={({ item }) => {
          const active = selectedType === item.value;
          return (
            <TouchableOpacity
              onPress={() => { setSelectedType(item.value); setPage(1); }}
              style={{
                backgroundColor: active ? Colors.primary : Colors.bgCard,
                borderRadius: 20,
                paddingHorizontal: 14,
                paddingVertical: 8,
                borderWidth: 1,
                borderColor: active ? Colors.primary : Colors.border,
              }}
            >
              <Text style={{ color: active ? Colors.white : Colors.textSecondary, fontSize: 13, fontWeight: '600' }}>
                {item.label}
              </Text>
            </TouchableOpacity>
          );
        }}
      />

      {/* Scan list */}
      <FlatList
        data={data?.scans ?? []}
        keyExtractor={(item) => item.id}
        contentContainerStyle={{ paddingHorizontal: 20, paddingBottom: 20 }}
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl refreshing={isRefetching} onRefresh={refetch} tintColor={Colors.primary} />
        }
        ListEmptyComponent={
          <View style={{ alignItems: 'center', paddingTop: 60 }}>
            <Text style={{ fontSize: 40 }}>📭</Text>
            <Text style={{ color: Colors.textSecondary, fontSize: 16, marginTop: 12 }}>
              {isLoading ? 'Loading...' : 'No scans yet'}
            </Text>
          </View>
        }
        renderItem={({ item }) => {
          const mod = SCAN_MODULES.find(m => m.id === item.scanType);
          return (
            <TouchableOpacity
              onPress={() => router.push({
                pathname: '/scan/[type]',
                params: { type: item.scanType },
              })}
              activeOpacity={0.85}
            >
              <Card padding={14} style={{ marginBottom: 10 }}>
                <View style={{ flexDirection: 'row', gap: 12, alignItems: 'flex-start' }}>
                  <View style={{
                    width: 44, height: 44, borderRadius: 22,
                    backgroundColor: `${mod?.color ?? Colors.primary}20`,
                    alignItems: 'center', justifyContent: 'center',
                    flexShrink: 0,
                  }}>
                    <Text style={{ fontSize: 20 }}>{mod?.icon ?? '🔍'}</Text>
                  </View>

                  <View style={{ flex: 1 }}>
                    <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
                      <Text style={{ color: Colors.textPrimary, fontWeight: '700', fontSize: 14 }}>
                        {mod?.title ?? item.scanType}
                      </Text>
                      <Text style={{ color: Colors.textMuted, fontSize: 11 }}>
                        {format(new Date(item.createdAt), 'MMM d, yyyy')}
                      </Text>
                    </View>
                    <Text style={{ color: Colors.textSecondary, fontSize: 13, marginTop: 3 }} numberOfLines={2}>
                      {item.detectionResult ?? 'Processing...'}
                    </Text>
                    {item.confidenceScore != null && (
                      <View style={{ marginTop: 8 }}>
                        <ConfidenceBadge score={item.confidenceScore} size="sm" />
                      </View>
                    )}
                    {item.nextScanDate && (
                      <Text style={{ color: Colors.info, fontSize: 11, marginTop: 6 }}>
                        ⏰ Next scan: {format(new Date(item.nextScanDate), 'MMM d')}
                      </Text>
                    )}
                  </View>
                </View>
              </Card>
            </TouchableOpacity>
          );
        }}
      />
    </SafeAreaView>
  );
}
