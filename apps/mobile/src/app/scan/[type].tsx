import React, { useState, useEffect } from 'react';
import {
  View, Text, Image, Alert, ActivityIndicator,
  ScrollView, TouchableOpacity,
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useQuery } from '@tanstack/react-query';
import ScanCamera from '../../components/camera/ScanCamera';
import ConfidenceBadge from '../../components/common/ConfidenceBadge';
import Card from '../../components/common/Card';
import Button from '../../components/common/Button';
import useScanStore from '../../store/scanStore';
import scanService from '../../services/scanService';
import {
  scheduleScanReminder,
  registerForPushNotificationsAsync,
} from '../../hooks/useNotifications';
import { Colors } from '../../theme/colors';
import { SCAN_MODULES, type ScanType, type ScanResult } from '../../types';
import { format } from 'date-fns';

type ViewState = 'camera' | 'processing' | 'result';

export default function ScanScreen() {
  const { type } = useLocalSearchParams<{ type: string }>();
  const router = useRouter();
  const { submitScan } = useScanStore();

  const [viewState, setViewState] = useState<ViewState>('camera');
  const [capturedUri, setCapturedUri] = useState<string | null>(null);
  const [scanResult, setScanResult] = useState<ScanResult | null>(null);
  const [reminderSet, setReminderSet] = useState(false);

  const module = SCAN_MODULES.find(m => m.id === type);

  // Load previous scan of same type for "Compare" button
  const { data: history } = useQuery({
    queryKey: ['scanHistory', type],
    queryFn: () => scanService.getHistory(type as ScanType, 1, 5),
    enabled: !!type,
  });

  // Auto-schedule notification when result has nextScanDate
  useEffect(() => {
    if (!scanResult?.nextScanDate || reminderSet) return;
    (async () => {
      const status = await registerForPushNotificationsAsync();
      if (status === 'granted') {
        await scheduleScanReminder(scanResult);
        setReminderSet(true);
      }
    })();
  }, [scanResult?.id]);

  if (!module) {
    return (
      <View style={{ flex: 1, backgroundColor: Colors.bgDark, alignItems: 'center', justifyContent: 'center' }}>
        <Text style={{ color: Colors.danger }}>Unknown scan type</Text>
      </View>
    );
  }

  const handleCapture = async (imageUri: string) => {
    setCapturedUri(imageUri);
    setViewState('processing');
    try {
      const result = await submitScan(module.id as ScanType, imageUri);
      setScanResult(result);
      setViewState('result');
    } catch (err: unknown) {
      Alert.alert('Scan Failed', err instanceof Error ? err.message : 'Please try again.');
      setViewState('camera');
    }
  };

  const handleRescan = () => {
    setCapturedUri(null);
    setScanResult(null);
    setReminderSet(false);
    setViewState('camera');
  };

  // Find previous scan of same type (excluding current)
  const previousScan = history?.scans.find(s => s.id !== scanResult?.id);

  // ── Processing ────────────────────────────────────────────
  if (viewState === 'processing') {
    return (
      <View style={{ flex: 1, backgroundColor: Colors.bgDark, alignItems: 'center', justifyContent: 'center', padding: 24 }}>
        {capturedUri && (
          <Image
            source={{ uri: capturedUri }}
            style={{ width: 200, height: 200, borderRadius: 16, marginBottom: 32, opacity: 0.6 }}
          />
        )}
        <ActivityIndicator size="large" color={module.color} />
        <Text style={{ color: Colors.textPrimary, fontSize: 18, fontWeight: '700', marginTop: 20, textAlign: 'center' }}>
          Analyzing {module.title}...
        </Text>
        <Text style={{ color: Colors.textSecondary, fontSize: 14, marginTop: 8, textAlign: 'center' }}>
          AI model is processing your scan
        </Text>
        <View style={{ flexDirection: 'row', gap: 6, marginTop: 24 }}>
          {['Detecting', 'Classifying', 'GPT Analysis'].map((step, i) => (
            <View key={i} style={{ alignItems: 'center', gap: 4 }}>
              <View style={{
                width: 8, height: 8, borderRadius: 4,
                backgroundColor: `${module.color}60`,
              }} />
              <Text style={{ color: Colors.textMuted, fontSize: 10 }}>{step}</Text>
            </View>
          ))}
        </View>
      </View>
    );
  }

  // ── Result ────────────────────────────────────────────────
  if (viewState === 'result' && scanResult) {
    const isPositive = scanResult.detectionResult?.toLowerCase().includes('detected') ||
                       scanResult.detectionResult?.toLowerCase().includes('likely');
    const isUrgent   = scanResult.aiRecommendation?.includes('URGENT') ||
                       scanResult.aiRecommendation?.includes('⚠️');

    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: Colors.bgDark }}>
        <ScrollView
          contentContainerStyle={{ padding: 20, paddingBottom: 40 }}
          showsVerticalScrollIndicator={false}
        >
          {/* Back */}
          <TouchableOpacity onPress={() => router.back()} style={{ marginBottom: 16 }}>
            <Text style={{ color: Colors.primary, fontSize: 15 }}>← Back</Text>
          </TouchableOpacity>

          {/* Scan image */}
          {capturedUri && (
            <Image
              source={{ uri: capturedUri }}
              style={{ width: '100%', height: 220, borderRadius: 20, marginBottom: 16 }}
              resizeMode="cover"
            />
          )}

          {/* Result header card */}
          <Card style={{ marginBottom: 12 }}>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 10 }}>
              <View style={{
                width: 52, height: 52, borderRadius: 26,
                backgroundColor: `${module.color}20`,
                alignItems: 'center', justifyContent: 'center',
                borderWidth: 1.5, borderColor: `${module.color}50`,
              }}>
                <Text style={{ fontSize: 24 }}>{module.icon}</Text>
              </View>
              <View style={{ flex: 1 }}>
                <Text style={{ color: Colors.textSecondary, fontSize: 12 }}>
                  {module.title} · {format(new Date(scanResult.createdAt), 'MMM d, h:mm a')}
                </Text>
                <Text style={{
                  color: isUrgent ? Colors.danger : isPositive ? Colors.warning : Colors.success,
                  fontSize: 15, fontWeight: '700', marginTop: 3,
                }} numberOfLines={2}>
                  {scanResult.detectionResult ?? 'Analysis complete'}
                </Text>
              </View>
            </View>
            {scanResult.confidenceScore != null && (
              <ConfidenceBadge score={scanResult.confidenceScore} />
            )}
          </Card>

          {/* Reminder card */}
          {scanResult.nextScanDate && (
            <Card style={{ marginBottom: 12, borderColor: `${Colors.info}50` }}>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
                <Text style={{ fontSize: 22 }}>⏰</Text>
                <View style={{ flex: 1 }}>
                  <Text style={{ color: Colors.info, fontWeight: '700', fontSize: 13 }}>
                    Next Scan Scheduled
                  </Text>
                  <Text style={{ color: Colors.textSecondary, fontSize: 13, marginTop: 2 }}>
                    {scanResult.nextScanRecommendation}
                  </Text>
                  <Text style={{ color: Colors.textMuted, fontSize: 12, marginTop: 3 }}>
                    📅 {format(new Date(scanResult.nextScanDate), 'EEEE, MMMM d yyyy')}
                  </Text>
                </View>
              </View>
              {reminderSet && (
                <View style={{
                  flexDirection: 'row', alignItems: 'center', gap: 6,
                  marginTop: 10, paddingTop: 10, borderTopWidth: 1, borderTopColor: Colors.border,
                }}>
                  <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: Colors.success }} />
                  <Text style={{ color: Colors.success, fontSize: 12, fontWeight: '600' }}>
                    Reminder notification scheduled ✓
                  </Text>
                </View>
              )}
            </Card>
          )}

          {/* AI Recommendations */}
          {scanResult.aiRecommendation && (
            <Card style={{
              marginBottom: 12,
              borderColor: isUrgent ? `${Colors.danger}50` : Colors.border,
            }}>
              <Text style={{ color: Colors.textPrimary, fontWeight: '700', fontSize: 14, marginBottom: 10 }}>
                {isUrgent ? '⚠️ ' : '💡 '}Recommendations
              </Text>
              {scanResult.aiRecommendation.split('\n').map((line, i) =>
                line.trim() ? (
                  <Text key={i} style={{ color: Colors.textSecondary, fontSize: 13, lineHeight: 20, marginBottom: 3 }}>
                    {line}
                  </Text>
                ) : null
              )}
            </Card>
          )}

          {/* Compare with previous scan */}
          {previousScan && (
            <TouchableOpacity
              onPress={() =>
                router.push({
                  pathname: '/compare/[scanId]',
                  params: { scanId: scanResult.id, previousId: previousScan.id },
                })
              }
              style={{
                flexDirection: 'row', alignItems: 'center', gap: 12,
                backgroundColor: Colors.bgCard, borderRadius: 16,
                padding: 14, marginBottom: 12,
                borderWidth: 1, borderColor: Colors.border,
              }}
            >
              <Text style={{ fontSize: 24 }}>📊</Text>
              <View style={{ flex: 1 }}>
                <Text style={{ color: Colors.textPrimary, fontWeight: '700', fontSize: 14 }}>
                  Compare with Previous Scan
                </Text>
                <Text style={{ color: Colors.textMuted, fontSize: 12, marginTop: 2 }}>
                  Previous: {format(new Date(previousScan.createdAt), 'MMM d, yyyy')}
                </Text>
              </View>
              <Text style={{ color: Colors.primary, fontSize: 18 }}>›</Text>
            </TouchableOpacity>
          )}

          {/* Disclaimer */}
          <View style={{
            backgroundColor: `${Colors.warning}10`, borderRadius: 12,
            padding: 12, marginBottom: 20,
            borderWidth: 1, borderColor: `${Colors.warning}30`,
          }}>
            <Text style={{ color: Colors.warning, fontSize: 12, lineHeight: 17 }}>
              ⚕️ AI-assisted screening tool — not a medical diagnosis. Always consult a licensed doctor before making health decisions.
            </Text>
          </View>

          {/* Actions */}
          <View style={{ gap: 10 }}>
            <Button title="📷 Scan Again" variant="outline" onPress={handleRescan} fullWidth />
            <Button
              title="📊 View History"
              variant="secondary"
              onPress={() => router.push('/(tabs)/history')}
              fullWidth
            />
          </View>
        </ScrollView>
      </SafeAreaView>
    );
  }

  // ── Camera ────────────────────────────────────────────────
  return (
    <ScanCamera
      module={module}
      onCapture={handleCapture}
      onClose={() => router.back()}
    />
  );
}
