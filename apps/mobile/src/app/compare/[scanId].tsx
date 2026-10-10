import ProtectedImage from '../../components/common/ProtectedImage';
/**
 * Scan Comparison Screen
 * Shows two scans of the same type side-by-side with trend analysis.
 * Route: /compare/[scanId]?previousId=xxx
 */
import React, { useMemo } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity,
  ActivityIndicator,
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useQuery } from '@tanstack/react-query';
import scanService from '../../services/scanService';
import Card from '../../components/common/Card';
import { Colors } from '../../theme/colors';
import { SCAN_MODULES } from '../../types';
import { format, differenceInDays } from 'date-fns';

export default function CompareScreen() {
  const { scanId, previousId } = useLocalSearchParams<{
    scanId: string;
    previousId: string;
  }>();
  const router = useRouter();

  const { data: currentScan, isLoading: loadingCurrent } = useQuery({
    queryKey: ['scan', scanId],
    queryFn: () => scanService.getScan(scanId),
    enabled: !!scanId,
  });

  const { data: previousScan, isLoading: loadingPrev } = useQuery({
    queryKey: ['scan', previousId],
    queryFn: () => scanService.getScan(previousId),
    enabled: !!previousId,
  });

  const isLoading = loadingCurrent || loadingPrev;

  const module = SCAN_MODULES.find(m => m.id === currentScan?.scanType);

  // ── Trend analysis ────────────────────────────────────────
  const trend = useMemo(() => {
    if (!currentScan || !previousScan) return null;
    const curr = currentScan.confidenceScore ?? 0;
    const prev = previousScan.confidenceScore ?? 0;
    const daysDiff = differenceInDays(
      new Date(currentScan.createdAt),
      new Date(previousScan.createdAt),
    );

    // Classifier confidence is not a measure of disease severity or recovery.
    return { trend: 'stable' as const, daysDiff, currScore: curr, prevScore: prev };
  }, [currentScan, previousScan]);

  const trendColor = Colors.warning;

  const trendIcon = '📷';
  const trendLabel = 'Clinical change not assessed';

  if (isLoading) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: Colors.bgDark, justifyContent: 'center', alignItems: 'center' }}>
        <ActivityIndicator size="large" color={Colors.primary} />
        <Text style={{ color: Colors.textSecondary, marginTop: 12 }}>Loading comparison...</Text>
      </SafeAreaView>
    );
  }

  if (!currentScan || !previousScan) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: Colors.bgDark, justifyContent: 'center', alignItems: 'center', padding: 24 }}>
        <Text style={{ color: Colors.danger, fontSize: 16, textAlign: 'center' }}>
          Could not load scans for comparison.
        </Text>
        <TouchableOpacity onPress={() => router.back()} style={{ marginTop: 16 }}>
          <Text style={{ color: Colors.primary }}>← Go Back</Text>
        </TouchableOpacity>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: Colors.bgDark }}>
      <ScrollView contentContainerStyle={{ padding: 20, paddingBottom: 40 }} showsVerticalScrollIndicator={false}>

        {/* Header */}
        <TouchableOpacity onPress={() => router.back()} style={{ marginBottom: 16 }}>
          <Text style={{ color: Colors.primary }}>← Back</Text>
        </TouchableOpacity>

        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 20 }}>
          <Text style={{ fontSize: 24 }}>{module?.icon ?? '🔍'}</Text>
          <View>
            <Text style={{ color: Colors.textPrimary, fontSize: 20, fontWeight: '800' }}>
              {module?.title ?? 'Scan'} Comparison
            </Text>
            <Text style={{ color: Colors.textMuted, fontSize: 13 }}>
              {trend?.daysDiff} days between scans
            </Text>
          </View>
        </View>

        {/* Trend banner */}
        {trend && (
          <View style={{
            backgroundColor: `${trendColor}15`,
            borderRadius: 16, padding: 16, marginBottom: 20,
            borderWidth: 1.5, borderColor: `${trendColor}40`,
            flexDirection: 'row', alignItems: 'center', gap: 12,
          }}>
            <Text style={{ fontSize: 32 }}>{trendIcon}</Text>
            <View style={{ flex: 1 }}>
              <Text style={{ color: trendColor, fontWeight: '800', fontSize: 16 }}>
                {trendLabel}
              </Text>
              <Text style={{ color: Colors.textSecondary, fontSize: 13, marginTop: 2 }}>
                Model output difference (not recovery): {((trend.currScore - trend.prevScore) * 100).toFixed(1)}% over {trend.daysDiff} days
              </Text>
            </View>
          </View>
        )}

        {/* Side-by-side scan images */}
        {(currentScan.imageUrl || previousScan.imageUrl) && (
          <View style={{ flexDirection: 'row', gap: 10, marginBottom: 20 }}>
            {[
              { scan: previousScan, label: 'Previous' },
              { scan: currentScan, label: 'Current' },
            ].map(({ scan, label }) => (
              <View key={label} style={{ flex: 1 }}>
                <Text style={{ color: Colors.textMuted, fontSize: 11, textAlign: 'center', marginBottom: 6 }}>
                  {label} · {format(new Date(scan.createdAt), 'MMM d')}
                </Text>
                {scan.imageUrl ? (
                  <ProtectedImage
                    uri={scan.imageUrl}
                    style={{ width: '100%', aspectRatio: 1, borderRadius: 14 }}
                    resizeMode="cover"
                  />
                ) : (
                  <View style={{
                    width: '100%', aspectRatio: 1, borderRadius: 14,
                    backgroundColor: Colors.bgCard, borderWidth: 1, borderColor: Colors.border,
                    justifyContent: 'center', alignItems: 'center',
                  }}>
                    <Text style={{ color: Colors.textMuted, fontSize: 11 }}>No image</Text>
                  </View>
                )}
              </View>
            ))}
          </View>
        )}

        {/* Detailed comparison table */}
        <Card style={{ marginBottom: 16 }}>
          <Text style={{ color: Colors.textPrimary, fontWeight: '700', fontSize: 15, marginBottom: 14 }}>
            Detailed Comparison
          </Text>

          {/* Column headers */}
          <View style={{ flexDirection: 'row', marginBottom: 10 }}>
            <View style={{ flex: 1.4 }} />
            <View style={{ flex: 1, alignItems: 'center' }}>
              <View style={{ backgroundColor: Colors.bgInput, borderRadius: 8, paddingHorizontal: 8, paddingVertical: 4 }}>
                <Text style={{ color: Colors.textMuted, fontSize: 11, fontWeight: '700' }}>
                  Previous
                </Text>
                <Text style={{ color: Colors.textMuted, fontSize: 10, textAlign: 'center' }}>
                  {format(new Date(previousScan.createdAt), 'MMM d')}
                </Text>
              </View>
            </View>
            <View style={{ flex: 1, alignItems: 'center' }}>
              <View style={{ backgroundColor: `${Colors.primary}20`, borderRadius: 8, paddingHorizontal: 8, paddingVertical: 4 }}>
                <Text style={{ color: Colors.primary, fontSize: 11, fontWeight: '700' }}>
                  Current
                </Text>
                <Text style={{ color: Colors.primary, fontSize: 10, textAlign: 'center' }}>
                  {format(new Date(currentScan.createdAt), 'MMM d')}
                </Text>
              </View>
            </View>
          </View>

          {/* Result row */}
          <CompareRow
            label="Result"
            prev={previousScan.detectionResult ?? '—'}
            curr={currentScan.detectionResult ?? '—'}
          />

          {/* Confidence row */}
          {previousScan.confidenceScore != null && currentScan.confidenceScore != null && (
            <CompareRow
              label="Confidence"
              prev={`${(previousScan.confidenceScore * 100).toFixed(0)}%`}
              curr={`${(currentScan.confidenceScore * 100).toFixed(0)}%`}
              highlight={trend?.trend}
            />
          )}

          {/* Status row */}
          <CompareRow
            label="Status"
            prev={previousScan.status}
            curr={currentScan.status}
          />
        </Card>

        {/* Current AI Recommendation */}
        {currentScan.aiRecommendation && (
          <Card style={{ marginBottom: 16 }}>
            <Text style={{ color: Colors.primary, fontWeight: '700', fontSize: 14, marginBottom: 10 }}>
              💡 Current Recommendations
            </Text>
            {currentScan.aiRecommendation.split('\n').map((line, i) =>
              line.trim() ? (
                <Text key={i} style={{ color: Colors.textSecondary, fontSize: 13, lineHeight: 20, marginBottom: 3 }}>
                  {line}
                </Text>
              ) : null
            )}
          </Card>
        )}

        {/* Next scan reminder */}
        {currentScan.nextScanDate && (
          <Card style={{ marginBottom: 16, borderColor: `${Colors.info}40` }}>
            <Text style={{ color: Colors.info, fontWeight: '700', marginBottom: 6 }}>
              ⏰ Next Scheduled Scan
            </Text>
            <Text style={{ color: Colors.textSecondary, fontSize: 14 }}>
              {currentScan.nextScanRecommendation ?? 'Rescan recommended'}
            </Text>
            <Text style={{ color: Colors.textMuted, fontSize: 13, marginTop: 4 }}>
              📅 {format(new Date(currentScan.nextScanDate), 'EEEE, MMMM d yyyy')}
            </Text>
            <Text style={{ color: Colors.success, fontSize: 12, marginTop: 6 }}>
              ✓ Reminder has been scheduled automatically
            </Text>
          </Card>
        )}

        {/* Disclaimer */}
        <View style={{
          backgroundColor: `${Colors.warning}10`, borderRadius: 12,
          padding: 12, marginBottom: 20, borderWidth: 1, borderColor: `${Colors.warning}30`,
        }}>
          <Text style={{ color: Colors.warning, fontSize: 11, lineHeight: 17 }}>
            ⚕️ AI comparison is for trend monitoring only. Consult a doctor for medical decisions.
          </Text>
        </View>

        {/* Action */}
        <TouchableOpacity
          onPress={() => router.push({ pathname: '/scan/[type]', params: { type: currentScan.scanType } })}
          style={{
            backgroundColor: Colors.primary, borderRadius: 16,
            paddingVertical: 16, alignItems: 'center',
          }}
        >
          <Text style={{ color: Colors.white, fontWeight: '700', fontSize: 16 }}>
            📷 Scan Again Now
          </Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

// ── Helper component ──────────────────────────────────────────
function CompareRow({
  label, prev, curr, highlight,
}: {
  label: string;
  prev: string;
  curr: string;
  highlight?: 'improved' | 'worsened' | 'stable';
}) {
  const currColor = highlight === 'improved' ? Colors.success :
                    highlight === 'worsened' ? Colors.danger : Colors.textPrimary;

  return (
    <View style={{
      flexDirection: 'row', paddingVertical: 10,
      borderBottomWidth: 1, borderBottomColor: Colors.border,
      alignItems: 'flex-start',
    }}>
      <View style={{ flex: 1.4 }}>
        <Text style={{ color: Colors.textMuted, fontSize: 12, fontWeight: '600' }}>{label}</Text>
      </View>
      <View style={{ flex: 1, paddingHorizontal: 4 }}>
        <Text style={{ color: Colors.textSecondary, fontSize: 12, textAlign: 'center' }} numberOfLines={2}>
          {prev}
        </Text>
      </View>
      <View style={{ flex: 1, paddingHorizontal: 4 }}>
        <Text style={{ color: currColor, fontSize: 12, fontWeight: '700', textAlign: 'center' }} numberOfLines={2}>
          {curr}
        </Text>
      </View>
    </View>
  );
}
