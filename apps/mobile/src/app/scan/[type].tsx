import React, { useState, useEffect } from 'react';
import {
  View, Text, Image, Alert, ActivityIndicator,
  ScrollView, TouchableOpacity,
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useQuery, useQueryClient } from '@tanstack/react-query';
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
import { pickScanPhoto } from '../../utils/pickScanPhoto';

type ViewState = 'consent' | 'camera' | 'review' | 'processing' | 'result';

export default function ScanScreen() {
  const { type } = useLocalSearchParams<{ type: string }>();
  const router = useRouter();
  const { submitScan } = useScanStore();
  const queryClient = useQueryClient();

  const [viewState, setViewState] = useState<ViewState>('consent');
  const [capturedUri, setCapturedUri] = useState<string | null>(null);
  const [scanResult, setScanResult] = useState<ScanResult | null>(null);
  const [reminderSet, setReminderSet] = useState(false);
  const [picking, setPicking] = useState(false);

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
  }, [scanResult, reminderSet]);

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
      await queryClient.invalidateQueries({ queryKey: ['scanHistory'] });
      await queryClient.invalidateQueries({ queryKey: ['recentScans'] });
      setScanResult(result);
      setViewState('result');
    } catch (err: unknown) {
      Alert.alert('Scan Failed', err instanceof Error ? err.message : 'Please try again.');
      setViewState('review');
    }
  };

  const reviewPhoto = (imageUri: string) => {
    setCapturedUri(imageUri);
    setViewState('review');
  };

  const handleGallery = async () => {
    if (picking) return;
    setPicking(true);
    try {
      const uri = await pickScanPhoto({ allowsEditing: module.captureMode !== 'upload_only' });
      if (uri) reviewPhoto(uri);
    } catch (error: unknown) {
      Alert.alert('Photo unavailable', error instanceof Error ? error.message : 'Please choose another photo.');
    } finally {
      setPicking(false);
    }
  };

  if (viewState === 'consent') return (
    <SafeAreaView style={{ flex: 1, backgroundColor: Colors.bgDark, padding: 24, justifyContent: 'center' }}>
      <Text style={{ color: Colors.textPrimary, fontSize: 26, fontWeight: '800', marginBottom: 16 }}>{module.icon} {module.title}</Text>
      <Text style={{ color: Colors.warning, fontSize: 17, fontWeight: '700', marginBottom: 16 }}>Research preview — disease detection is not validated</Text>
      <Text style={{ color: Colors.textSecondary, fontSize: 16, lineHeight: 25, marginBottom: 24 }}>Continuing will upload and save your photo to the local development server under your account. This version provides photo history, not a diagnosis or a medicine recommendation. Use test photos. A clinician must assess symptoms and prescriptions.</Text>
      {module.captureMode === 'upload_only' && <Text style={{ color: Colors.textPrimary, lineHeight: 24, marginBottom: 20 }}>{module.instructions}</Text>}
      {module.captureMode !== 'upload_only' && <Button title="I agree — take a photo" onPress={() => setViewState('camera')} disabled={picking} fullWidth />}
      <Button title={module.captureMode === 'upload_only' ? 'I agree — choose fundus image' : 'I agree — upload a saved photo'} variant={module.captureMode === 'upload_only' ? 'primary' : 'secondary'} onPress={handleGallery} loading={picking} fullWidth style={{ marginTop: 12 }} />
      <Button title="Go back" variant="outline" onPress={() => router.back()} fullWidth style={{ marginTop: 12 }} />
    </SafeAreaView>
  );

  const handleRescan = () => {
    setCapturedUri(null);
    setScanResult(null);
    setReminderSet(false);
    setViewState('consent');
  };

  // Find previous scan of same type (excluding current)
  const previousScan = history?.scans.find(s => s.id !== scanResult?.id);

  if (viewState === 'review' && capturedUri) return (
    <SafeAreaView style={{ flex: 1, backgroundColor: Colors.bgDark }}>
      <ScrollView contentContainerStyle={{ padding: 24, gap: 16 }}>
        <Text style={{ color: Colors.textPrimary, fontSize: 24, fontWeight: '800' }}>Review your photo</Text>
        <Text style={{ color: Colors.textSecondary }}>{module.title} · {module.targetArea}</Text>
        <Image source={{ uri: capturedUri }} style={{ width: '100%', height: 320, borderRadius: 16 }} resizeMode="contain" accessibilityLabel="Selected scan photo" />
        <Text style={{ color: Colors.textSecondary, lineHeight: 22 }}>Check that the affected area is clear and well lit. This photo stays on your device until you select Upload and save. The current preview saves photo history and cannot determine a disease.</Text>
        {module.captureMode === 'upload_only' && <Text style={{ color: Colors.textPrimary, lineHeight: 22 }}>{module.instructions} Image modality is not automatically verified in this preview.</Text>}
        <Button title={module.captureMode === 'upload_only' ? 'Confirm fundus image and save' : 'Upload and save photo'} onPress={() => handleCapture(capturedUri)} disabled={picking} fullWidth />
        <Button title="Choose another photo" variant="secondary" onPress={handleGallery} loading={picking} fullWidth />
        {module.captureMode !== 'upload_only' && <Button title="Take a new photo" variant="outline" onPress={() => setViewState('camera')} disabled={picking} fullWidth />}
        <Button title="Cancel" variant="ghost" onPress={() => { setCapturedUri(null); setViewState('consent'); }} disabled={picking} fullWidth />
      </ScrollView>
    </SafeAreaView>
  );

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
          Saving {module.title} photo...
        </Text>
        <Text style={{ color: Colors.textSecondary, fontSize: 14, marginTop: 8, textAlign: 'center' }}>
          Uploading your photo to your private history
        </Text>
        <View style={{ flexDirection: 'row', gap: 6, marginTop: 24 }}>
          {['Uploading', 'Checking image', 'Saving'].map((step, i) => (
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
                  color: isUrgent ? Colors.danger : Colors.warning,
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
      onCapture={reviewPhoto}
      onClose={() => setViewState('consent')}
    />
  );
}
