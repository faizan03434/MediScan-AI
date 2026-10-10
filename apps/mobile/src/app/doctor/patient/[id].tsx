import ProtectedImage from '../../../components/common/ProtectedImage';
import React, { useState } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity,
  ActivityIndicator,
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useQuery } from '@tanstack/react-query';
import doctorService from '../../../services/doctorService';
import Card from '../../../components/common/Card';
import ConfidenceBadge from '../../../components/common/ConfidenceBadge';
import { Colors } from '../../../theme/colors';
import { SCAN_MODULES } from '../../../types';
import { format } from 'date-fns';

export default function PatientDetailScreen() {
  const { id: patientId } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const [page, setPage] = useState(1);

  const { data: patients } = useQuery({
    queryKey: ['myPatients'],
    queryFn: doctorService.getMyPatients,
  });
  const patient = patients?.find(p => p.userId === patientId);

  const { data: scanHistory, isLoading } = useQuery({
    queryKey: ['patientScans', patientId, page],
    queryFn: () => doctorService.getPatientScans(patientId, page),
    enabled: !!patientId,
  });

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: Colors.bgDark }}>
      <ScrollView contentContainerStyle={{ paddingBottom: 40 }} showsVerticalScrollIndicator={false}>

        {/* Header */}
        <View style={{ padding: 20, borderBottomWidth: 1, borderBottomColor: Colors.border }}>
          <TouchableOpacity onPress={() => router.back()} style={{ marginBottom: 14 }}>
            <Text style={{ color: Colors.primary }}>← Patients</Text>
          </TouchableOpacity>

          {patient && (
            <>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 14 }}>
                <View style={{
                  width: 58, height: 58, borderRadius: 29,
                  backgroundColor: `${Colors.primary}20`,
                  alignItems: 'center', justifyContent: 'center',
                  borderWidth: 2, borderColor: `${Colors.primary}40`,
                }}>
                  <Text style={{ fontSize: 26 }}>{patient.gender === 'Female' ? '👩' : '👨'}</Text>
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={{ color: Colors.textPrimary, fontSize: 20, fontWeight: '800' }}>
                    {patient.fullName}
                  </Text>
                  <Text style={{ color: Colors.textSecondary, fontSize: 13, marginTop: 2 }}>
                    {patient.email}
                  </Text>
                  <View style={{ flexDirection: 'row', gap: 10, marginTop: 5 }}>
                    {patient.ageYears != null && (
                      <Text style={{ color: Colors.textMuted, fontSize: 12 }}>🎂 {patient.ageYears} yrs</Text>
                    )}
                    {patient.gender && (
                      <Text style={{ color: Colors.textMuted, fontSize: 12 }}>⚧ {patient.gender}</Text>
                    )}
                    {patient.bloodGroup && (
                      <Text style={{ color: Colors.textMuted, fontSize: 12 }}>🩸 {patient.bloodGroup}</Text>
                    )}
                  </View>
                </View>
              </View>

              {/* Stats */}
              <View style={{ flexDirection: 'row', gap: 10, marginTop: 14 }}>
                {[
                  { label: 'Total Scans', value: String(patient.totalScans), icon: '📷' },
                  {
                    label: 'Consent Until',
                    value: patient.consentExpiresAt
                      ? format(new Date(patient.consentExpiresAt), 'MMM d, yy')
                      : 'No expiry',
                    icon: '🔐',
                  },
                ].map(s => (
                  <View key={s.label} style={{
                    flex: 1, backgroundColor: Colors.bgCard, borderRadius: 12,
                    padding: 10, borderWidth: 1, borderColor: Colors.border,
                  }}>
                    <Text style={{ fontSize: 16 }}>{s.icon}</Text>
                    <Text style={{ color: Colors.textPrimary, fontWeight: '700', fontSize: 15, marginTop: 3 }}>
                      {s.value}
                    </Text>
                    <Text style={{ color: Colors.textMuted, fontSize: 11 }}>{s.label}</Text>
                  </View>
                ))}
              </View>
            </>
          )}
        </View>

        {/* Scans */}
        <View style={{ padding: 20 }}>
          <Text style={{ color: Colors.textPrimary, fontWeight: '700', fontSize: 17, marginBottom: 14 }}>
            Scan History
          </Text>

          {isLoading ? (
            <ActivityIndicator color={Colors.primary} style={{ marginTop: 20 }} />
          ) : !scanHistory?.scans.length ? (
            <View style={{ alignItems: 'center', paddingVertical: 32 }}>
              <Text style={{ fontSize: 36 }}>📭</Text>
              <Text style={{ color: Colors.textSecondary, marginTop: 10 }}>No scans yet</Text>
            </View>
          ) : (
            <>
              {scanHistory.scans.map(scan => {
                const mod = SCAN_MODULES.find(m => m.id === scan.scanType);
                const isPositive = scan.detectionResult?.toLowerCase().includes('detected');
                const isUrgent   = scan.aiRecommendation?.includes('URGENT') || scan.aiRecommendation?.includes('⚠️');

                return (
                  <TouchableOpacity
                    key={scan.id}
                    activeOpacity={0.85}
                    onPress={() => router.push({
                      pathname: '/doctor/patient/scan/[scanId]',
                      params: { scanId: scan.id, patientId },
                    })}
                  >
                    <Card padding={14} style={{ marginBottom: 10 }}>
                      <View style={{ flexDirection: 'row', gap: 12, alignItems: 'flex-start' }}>
                        {scan.imageUrl ? (
                          <ProtectedImage
                            uri={scan.imageUrl}
                            style={{ width: 50, height: 50, borderRadius: 10 }}
                            resizeMode="cover"
                          />
                        ) : (
                          <View style={{
                            width: 50, height: 50, borderRadius: 10,
                            backgroundColor: `${mod?.color ?? Colors.primary}20`,
                            alignItems: 'center', justifyContent: 'center',
                          }}>
                            <Text style={{ fontSize: 22 }}>{mod?.icon ?? '🔍'}</Text>
                          </View>
                        )}

                        <View style={{ flex: 1 }}>
                          <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
                            <Text style={{ color: Colors.textPrimary, fontWeight: '700', fontSize: 14 }}>
                              {mod?.title ?? scan.scanType}
                            </Text>
                            <Text style={{ color: Colors.textMuted, fontSize: 11 }}>
                              {format(new Date(scan.createdAt), 'MMM d')}
                            </Text>
                          </View>

                          <Text style={{
                            color: isUrgent ? Colors.danger : isPositive ? Colors.warning : Colors.success,
                            fontSize: 12, marginTop: 4,
                          }} numberOfLines={2}>
                            {scan.detectionResult ?? 'Processing...'}
                          </Text>

                          {scan.confidenceScore != null && (
                            <View style={{ marginTop: 6 }}>
                              <ConfidenceBadge score={scan.confidenceScore} size="sm" />
                            </View>
                          )}
                        </View>
                        <Text style={{ color: Colors.primary, fontSize: 18, alignSelf: 'center' }}>›</Text>
                      </View>
                    </Card>
                  </TouchableOpacity>
                );
              })}

              {/* Pagination */}
              <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginTop: 12 }}>
                <TouchableOpacity
                  onPress={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  style={{ opacity: page <= 1 ? 0.4 : 1 }}
                >
                  <Text style={{ color: Colors.primary }}>← Prev</Text>
                </TouchableOpacity>
                <Text style={{ color: Colors.textMuted, fontSize: 13 }}>Page {page}</Text>
                <TouchableOpacity
                  onPress={() => setPage(p => p + 1)}
                  disabled={(scanHistory?.scans.length ?? 0) < 10}
                  style={{ opacity: (scanHistory?.scans.length ?? 0) < 10 ? 0.4 : 1 }}
                >
                  <Text style={{ color: Colors.primary }}>Next →</Text>
                </TouchableOpacity>
              </View>
            </>
          )}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}
