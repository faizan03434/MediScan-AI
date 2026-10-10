/**
 * Doctor Portal — Entry Screen
 * Shows doctor's patient list + consent management tab.
 * Only accessible to users with role = "Doctor".
 */
import React, { useState } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity,
  RefreshControl, ActivityIndicator,
} from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useQuery } from '@tanstack/react-query';
import doctorService from '../../services/doctorService';
import useAuthStore from '../../store/authStore';
import Card from '../../components/common/Card';
import { Colors } from '../../theme/colors';
import { format } from 'date-fns';

type Tab = 'patients' | 'consents';

export default function DoctorPortalScreen() {
  const router = useRouter();
  const { user } = useAuthStore();
  const [tab, setTab] = useState<Tab>('patients');

  const isDoctor = user?.role === 'Doctor' || user?.role === 'Admin';

  const { data: patients, isLoading: loadingPatients, refetch: refetchPatients, isRefetching: refetchingPatients } = useQuery({
    queryKey: ['myPatients'],
    queryFn: doctorService.getMyPatients,
    enabled: isDoctor,
  });

  const { data: sentConsents, isLoading: loadingConsents, refetch: refetchConsents } = useQuery({
    queryKey: ['sentConsents'],
    queryFn: doctorService.getSentConsents,
    enabled: isDoctor,
  });

  if (!isDoctor) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: Colors.bgDark, justifyContent: 'center', alignItems: 'center', padding: 24 }}>
        <Text style={{ fontSize: 48, marginBottom: 16 }}>🔒</Text>
        <Text style={{ color: Colors.textPrimary, fontSize: 18, fontWeight: '700', textAlign: 'center' }}>
          Doctor Access Only
        </Text>
        <Text style={{ color: Colors.textSecondary, fontSize: 14, textAlign: 'center', marginTop: 8 }}>
          This section is for verified doctors only.{'\n'}
          Contact admin to upgrade your account role.
        </Text>
        <TouchableOpacity onPress={() => router.back()} style={{ marginTop: 24 }}>
          <Text style={{ color: Colors.primary }}>← Go Back</Text>
        </TouchableOpacity>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: Colors.bgDark }}>
      {/* Header */}
      <View style={{
        paddingHorizontal: 20, paddingTop: 16, paddingBottom: 12,
        borderBottomWidth: 1, borderBottomColor: Colors.border,
      }}>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
          <View>
            <Text style={{ color: Colors.textPrimary, fontSize: 22, fontWeight: '800' }}>
              👨‍⚕️ Doctor Portal
            </Text>
            <Text style={{ color: Colors.textSecondary, fontSize: 13, marginTop: 2 }}>
              Dr. {user?.fullName}
            </Text>
          </View>
          <TouchableOpacity
            onPress={() => router.push('/doctor/request-access')}
            style={{
              backgroundColor: Colors.primary, borderRadius: 12,
              paddingHorizontal: 14, paddingVertical: 9,
            }}
          >
            <Text style={{ color: Colors.white, fontSize: 13, fontWeight: '700' }}>
              + Request Access
            </Text>
          </TouchableOpacity>
        </View>

        {/* Stats strip */}
        <View style={{ flexDirection: 'row', gap: 12, marginTop: 12 }}>
          {[
            { label: 'Patients', value: patients?.length ?? 0, icon: '👥' },
            { label: 'Pending Requests', value: sentConsents?.filter(c => c.status === 'Pending').length ?? 0, icon: '⏳' },
          ].map(stat => (
            <View key={stat.label} style={{
              flex: 1, backgroundColor: Colors.bgCard, borderRadius: 12,
              padding: 10, flexDirection: 'row', alignItems: 'center', gap: 8,
              borderWidth: 1, borderColor: Colors.border,
            }}>
              <Text style={{ fontSize: 18 }}>{stat.icon}</Text>
              <View>
                <Text style={{ color: Colors.textPrimary, fontWeight: '800', fontSize: 18 }}>
                  {stat.value}
                </Text>
                <Text style={{ color: Colors.textMuted, fontSize: 11 }}>{stat.label}</Text>
              </View>
            </View>
          ))}
        </View>
      </View>

      {/* Tabs */}
      <View style={{ flexDirection: 'row', paddingHorizontal: 20, paddingTop: 14, gap: 8 }}>
        {([
          { key: 'patients' as Tab, label: '👥 My Patients' },
          { key: 'consents' as Tab, label: '📋 Consent Requests' },
        ]).map(t => (
          <TouchableOpacity
            key={t.key}
            onPress={() => setTab(t.key)}
            style={{
              flex: 1, paddingVertical: 10, borderRadius: 12,
              backgroundColor: tab === t.key ? Colors.primary : Colors.bgCard,
              borderWidth: 1, borderColor: tab === t.key ? Colors.primary : Colors.border,
              alignItems: 'center',
            }}
          >
            <Text style={{
              color: tab === t.key ? Colors.white : Colors.textSecondary,
              fontSize: 13, fontWeight: '600',
            }}>
              {t.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Content */}
      <ScrollView
        contentContainerStyle={{ padding: 20, paddingBottom: 40 }}
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl
            refreshing={refetchingPatients}
            onRefresh={() => { refetchPatients(); refetchConsents(); }}
            tintColor={Colors.primary}
          />
        }
      >
        {tab === 'patients' && (
          <>
            {loadingPatients ? (
              <ActivityIndicator color={Colors.primary} style={{ marginTop: 40 }} />
            ) : patients?.length === 0 ? (
              <View style={{ alignItems: 'center', paddingTop: 40 }}>
                <Text style={{ fontSize: 40 }}>👥</Text>
                <Text style={{ color: Colors.textSecondary, fontSize: 16, marginTop: 12 }}>
                  No patients yet
                </Text>
                <Text style={{ color: Colors.textMuted, fontSize: 13, marginTop: 6, textAlign: 'center' }}>
                  Request access from patients to start viewing their health data.
                </Text>
              </View>
            ) : (
              patients?.map(patient => (
                <TouchableOpacity
                  key={patient.userId}
                  onPress={() => router.push({
                    pathname: '/doctor/patient/[id]',
                    params: { id: patient.userId },
                  })}
                  activeOpacity={0.8}
                >
                  <Card padding={14} style={{ marginBottom: 10 }}>
                    <View style={{ flexDirection: 'row', alignItems: 'flex-start', gap: 12 }}>
                      {/* Avatar */}
                      <View style={{
                        width: 46, height: 46, borderRadius: 23,
                        backgroundColor: `${Colors.primary}20`,
                        alignItems: 'center', justifyContent: 'center',
                        borderWidth: 1.5, borderColor: `${Colors.primary}40`,
                        flexShrink: 0,
                      }}>
                        <Text style={{ fontSize: 20 }}>
                          {patient.gender === 'Female' ? '👩' : '👨'}
                        </Text>
                      </View>

                      <View style={{ flex: 1 }}>
                        <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
                          <Text style={{ color: Colors.textPrimary, fontWeight: '700', fontSize: 15 }}>
                            {patient.fullName}
                          </Text>
                          <Text style={{ color: Colors.textMuted, fontSize: 11 }}>
                            {patient.ageYears ? `${patient.ageYears} yrs` : ''}
                            {patient.ageYears && patient.bloodGroup ? ' · ' : ''}
                            {patient.bloodGroup ?? ''}
                          </Text>
                        </View>

                        <Text style={{ color: Colors.textMuted, fontSize: 12, marginTop: 1 }}>
                          {patient.email}
                        </Text>

                        {/* Last scan */}
                        {patient.lastScanResult && (
                          <View style={{
                            flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 6,
                          }}>
                            <View style={{ width: 6, height: 6, borderRadius: 3, backgroundColor: Colors.warning }} />
                            <Text style={{ color: Colors.textSecondary, fontSize: 12 }} numberOfLines={1}>
                              {patient.lastScanResult}
                            </Text>
                          </View>
                        )}

                        {/* Stats row */}
                        <View style={{ flexDirection: 'row', gap: 12, marginTop: 8 }}>
                          <View style={{
                            backgroundColor: `${Colors.primary}15`, borderRadius: 8,
                            paddingHorizontal: 8, paddingVertical: 4,
                          }}>
                            <Text style={{ color: Colors.primary, fontSize: 11, fontWeight: '600' }}>
                              📷 {patient.totalScans} scans
                            </Text>
                          </View>
                          {patient.consentExpiresAt && (
                            <View style={{
                              backgroundColor: `${Colors.warning}15`, borderRadius: 8,
                              paddingHorizontal: 8, paddingVertical: 4,
                            }}>
                              <Text style={{ color: Colors.warning, fontSize: 11, fontWeight: '600' }}>
                                Expires {format(new Date(patient.consentExpiresAt), 'MMM d')}
                              </Text>
                            </View>
                          )}
                        </View>
                      </View>
                      <Text style={{ color: Colors.primary, fontSize: 18, alignSelf: 'center' }}>›</Text>
                    </View>
                  </Card>
                </TouchableOpacity>
              ))
            )}
          </>
        )}

        {tab === 'consents' && (
          <>
            {loadingConsents ? (
              <ActivityIndicator color={Colors.primary} style={{ marginTop: 40 }} />
            ) : sentConsents?.length === 0 ? (
              <View style={{ alignItems: 'center', paddingTop: 40 }}>
                <Text style={{ fontSize: 40 }}>📋</Text>
                <Text style={{ color: Colors.textSecondary, fontSize: 16, marginTop: 12 }}>
                  No consent requests yet
                </Text>
              </View>
            ) : (
              sentConsents?.map(consent => {
                const statusColor = consent.status === 'Granted' ? Colors.success
                  : consent.status === 'Pending' ? Colors.warning : Colors.danger;
                const statusIcon = consent.status === 'Granted' ? '✅'
                  : consent.status === 'Pending' ? '⏳' : '❌';

                return (
                  <Card key={consent.id} padding={14} style={{ marginBottom: 10 }}>
                    <View style={{ flexDirection: 'row', alignItems: 'flex-start', gap: 10 }}>
                      <Text style={{ fontSize: 20 }}>{statusIcon}</Text>
                      <View style={{ flex: 1 }}>
                        <Text style={{ color: Colors.textPrimary, fontWeight: '700', fontSize: 14 }}>
                          {consent.patientName}
                        </Text>
                        <Text style={{ color: Colors.textMuted, fontSize: 12, marginTop: 1 }}>
                          {consent.patientEmail}
                        </Text>
                        <View style={{
                          flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 8,
                        }}>
                          <View style={{
                            backgroundColor: `${statusColor}20`,
                            borderRadius: 8, paddingHorizontal: 8, paddingVertical: 3,
                          }}>
                            <Text style={{ color: statusColor, fontSize: 11, fontWeight: '700' }}>
                              {consent.status}
                            </Text>
                          </View>
                          <Text style={{ color: Colors.textMuted, fontSize: 11 }}>
                            {format(new Date(consent.requestedAt), 'MMM d, yyyy')}
                          </Text>
                        </View>
                        {consent.consentMessage && (
                          <Text style={{ color: Colors.textSecondary, fontSize: 12, marginTop: 6 }}
                            numberOfLines={2}>
                            {consent.consentMessage}
                          </Text>
                        )}
                      </View>
                    </View>
                  </Card>
                );
              })
            )}
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}
