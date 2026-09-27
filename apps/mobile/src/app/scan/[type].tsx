import React, { useState } from 'react';
import { View, Text, Image, Alert, ActivityIndicator, ScrollView, TouchableOpacity } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import ScanCamera from '../../components/camera/ScanCamera';
import ConfidenceBadge from '../../components/common/ConfidenceBadge';
import Card from '../../components/common/Card';
import Button from '../../components/common/Button';
import useScanStore from '../../store/scanStore';
import { Colors } from '../../theme/colors';
import { SCAN_MODULES, type ScanType, type ScanResult } from '../../types';
import { format } from 'date-fns';

type ViewState = 'camera' | 'processing' | 'result';

export default function ScanScreen() {
  const { type } = useLocalSearchParams<{ type: string }>();
  const router = useRouter();
  const { submitScan, isScanning } = useScanStore();

  const [viewState, setViewState] = useState<ViewState>('camera');
  const [capturedUri, setCapturedUri] = useState<string | null>(null);
  const [scanResult, setScanResult] = useState<ScanResult | null>(null);

  const module = SCAN_MODULES.find(m => m.id === type);

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
    setViewState('camera');
  };

  // ── Processing screen ───────────────────────────────────────
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
      </View>
    );
  }

  // ── Result screen ───────────────────────────────────────────
  if (viewState === 'result' && scanResult) {
    const isPositive = scanResult.detectionResult?.toLowerCase().includes('detected') ||
                       scanResult.detectionResult?.toLowerCase().includes('likely');
    const isUrgent = scanResult.aiRecommendation?.includes('URGENT') ||
                     scanResult.aiRecommendation?.includes('⚠️');

    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: Colors.bgDark }}>
        <ScrollView contentContainerStyle={{ padding: 20 }} showsVerticalScrollIndicator={false}>
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

          {/* Result header */}
          <Card style={{ marginBottom: 14 }}>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 10 }}>
              <View style={{
                width: 48, height: 48, borderRadius: 24,
                backgroundColor: `${module.color}20`,
                alignItems: 'center', justifyContent: 'center',
              }}>
                <Text style={{ fontSize: 22 }}>{module.icon}</Text>
              </View>
              <View style={{ flex: 1 }}>
                <Text style={{ color: Colors.textSecondary, fontSize: 12 }}>
                  {module.title} — {format(new Date(scanResult.createdAt), 'MMM d, h:mm a')}
                </Text>
                <Text style={{
                  color: isUrgent ? Colors.danger : isPositive ? Colors.warning : Colors.success,
                  fontSize: 15, fontWeight: '700', marginTop: 2,
                }} numberOfLines={2}>
                  {scanResult.detectionResult ?? 'Analysis complete'}
                </Text>
              </View>
            </View>
            {scanResult.confidenceScore != null && (
              <ConfidenceBadge score={scanResult.confidenceScore} />
            )}
          </Card>

          {/* Next scan reminder */}
          {scanResult.nextScanRecommendation && (
            <Card style={{ marginBottom: 14, borderColor: `${Colors.info}40` }}>
              <Text style={{ color: Colors.info, fontWeight: '700', fontSize: 13, marginBottom: 4 }}>
                ⏰ Next Scan Reminder
              </Text>
              <Text style={{ color: Colors.textSecondary, fontSize: 13 }}>
                {scanResult.nextScanRecommendation}
              </Text>
              {scanResult.nextScanDate && (
                <Text style={{ color: Colors.textMuted, fontSize: 12, marginTop: 4 }}>
                  Scheduled: {format(new Date(scanResult.nextScanDate), 'MMMM d, yyyy')}
                </Text>
              )}
            </Card>
          )}

          {/* AI Recommendations */}
          {scanResult.aiRecommendation && (
            <Card style={{ marginBottom: 14, borderColor: isUrgent ? `${Colors.danger}40` : Colors.border }}>
              <Text style={{ color: Colors.textPrimary, fontWeight: '700', fontSize: 14, marginBottom: 10 }}>
                {isUrgent ? '⚠️ ' : '💡 '}Recommendations
              </Text>
              {scanResult.aiRecommendation.split('\n').map((line, i) => (
                line.trim() ? (
                  <Text key={i} style={{ color: Colors.textSecondary, fontSize: 13, lineHeight: 20, marginBottom: 4 }}>
                    {line}
                  </Text>
                ) : null
              ))}
            </Card>
          )}

          {/* Disclaimer */}
          <View style={{
            backgroundColor: `${Colors.warning}10`,
            borderRadius: 12, padding: 12, marginBottom: 20,
            borderWidth: 1, borderColor: `${Colors.warning}30`,
          }}>
            <Text style={{ color: Colors.warning, fontSize: 12, lineHeight: 17 }}>
              ⚕️ This is an AI-assisted screening tool and does NOT replace professional medical advice. Always consult a licensed doctor before making health decisions.
            </Text>
          </View>

          <View style={{ gap: 10 }}>
            <Button
              title="Scan Again"
              variant="outline"
              onPress={handleRescan}
              fullWidth
            />
            <Button
              title="View Full History"
              variant="secondary"
              onPress={() => router.push('/(tabs)/history')}
              fullWidth
            />
          </View>
        </ScrollView>
      </SafeAreaView>
    );
  }

  // ── Camera screen ───────────────────────────────────────────
  return (
    <ScanCamera
      module={module}
      onCapture={handleCapture}
      onClose={() => router.back()}
    />
  );
}
