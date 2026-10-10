import React from 'react';
import { ActivityIndicator, ScrollView, Text } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useQuery } from '@tanstack/react-query';
import doctorService from '../../../../services/doctorService';
import Button from '../../../../components/common/Button';
import { Colors } from '../../../../theme/colors';

export default function PatientScanScreen() {
  const { scanId, patientId } = useLocalSearchParams<{ scanId: string; patientId: string }>();
  const router = useRouter();
  const { data: scan, isLoading, error } = useQuery({ queryKey: ['patientScan', patientId, scanId],
    queryFn: () => doctorService.getPatientScan(patientId, scanId), enabled: !!patientId && !!scanId });
  return <SafeAreaView style={{ flex: 1, backgroundColor: Colors.bgDark }}>
    <ScrollView contentContainerStyle={{ padding: 20, gap: 16 }}>
      <Button title="Back to patient" variant="outline" onPress={() => router.back()} />
      {isLoading && <ActivityIndicator color={Colors.primary} />}
      {error && <Text style={{ color: Colors.danger }}>Record unavailable. Check active patient consent.</Text>}
      {scan && <>
        <Text style={{ color: Colors.textPrimary, fontSize: 24, fontWeight: '700' }}>{scan.scanType}</Text>
        <Text style={{ color: Colors.textSecondary }}>{new Date(scan.createdAt).toLocaleString()}</Text>
        <Text style={{ color: Colors.warning }}>{scan.detectionResult}</Text>
        <Text style={{ color: Colors.textSecondary, lineHeight: 24 }}>{scan.aiRecommendation}</Text>
        <Text style={{ color: Colors.textMuted }}>Clinical change is not assessed in this preview. Photo sharing with clinicians is pending the complete consent-scope review.</Text>
      </>}
    </ScrollView>
  </SafeAreaView>;
}
