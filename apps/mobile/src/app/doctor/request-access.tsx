/**
 * Doctor: Request patient consent form.
 */
import React, { useState } from 'react';
import {
  View, Text, ScrollView, TextInput,
  TouchableOpacity, Alert,
  Switch, KeyboardAvoidingView, Platform,
} from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useQueryClient } from '@tanstack/react-query';
import doctorService from '../../services/doctorService';
import Button from '../../components/common/Button';
import Card from '../../components/common/Card';
import { Colors } from '../../theme/colors';
import { SCAN_MODULES } from '../../types';

export default function RequestAccessScreen() {
  const router = useRouter();
  const qc = useQueryClient();

  const [patientEmail, setPatientEmail] = useState('');
  const [message, setMessage] = useState('');
  const [expiryDays, setExpiryDays] = useState<string>('90');
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);
  const [allTypes, setAllTypes] = useState(true);
  const [loading, setLoading] = useState(false);

  const toggleType = (type: string) => {
    setSelectedTypes(prev =>
      prev.includes(type) ? prev.filter(t => t !== type) : [...prev, type],
    );
  };

  const handleSubmit = async () => {
    if (!patientEmail.trim() || !patientEmail.includes('@')) {
      Alert.alert('Invalid Email', 'Please enter a valid patient email address.');
      return;
    }

    setLoading(true);
    try {
      await doctorService.requestConsent({
        patientEmail: patientEmail.trim(),
        message: message.trim() || undefined,
        scanTypes: allTypes ? undefined : selectedTypes,
        expiryDays: expiryDays ? parseInt(expiryDays) : undefined,
      });

      qc.invalidateQueries({ queryKey: ['sentConsents'] });
      Alert.alert(
        'Request Sent ✓',
        `Consent request sent to ${patientEmail}. They will be notified and can accept or deny access.`,
        [{ text: 'OK', onPress: () => router.back() }],
      );
    } catch (err: unknown) {
      Alert.alert('Failed', err instanceof Error ? err.message : 'Could not send request.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: Colors.bgDark }}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
        <ScrollView
          contentContainerStyle={{ padding: 20, paddingBottom: 40 }}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          {/* Header */}
          <TouchableOpacity onPress={() => router.back()} style={{ marginBottom: 16 }}>
            <Text style={{ color: Colors.primary }}>← Back</Text>
          </TouchableOpacity>

          <Text style={{ color: Colors.textPrimary, fontSize: 22, fontWeight: '800', marginBottom: 4 }}>
            Request Patient Access
          </Text>
          <Text style={{ color: Colors.textSecondary, fontSize: 13, marginBottom: 20, lineHeight: 19 }}>
            The patient will receive a notification to accept or deny your request.
            All access is logged per HIPAA requirements.
          </Text>

          {/* Patient email */}
          <Card style={{ marginBottom: 14 }}>
            <Text style={{ color: Colors.textSecondary, fontSize: 13, fontWeight: '600', marginBottom: 8 }}>
              Patient Email Address *
            </Text>
            <TextInput
              style={{
                color: Colors.textPrimary, fontSize: 15, paddingVertical: 12,
                paddingHorizontal: 14, backgroundColor: Colors.bgInput,
                borderRadius: 12, borderWidth: 1.5, borderColor: Colors.border,
              }}
              placeholder="patient@example.com"
              placeholderTextColor={Colors.textMuted}
              value={patientEmail}
              onChangeText={setPatientEmail}
              keyboardType="email-address"
              autoCapitalize="none"
              autoComplete="email"
            />
          </Card>

          {/* Message */}
          <Card style={{ marginBottom: 14 }}>
            <Text style={{ color: Colors.textSecondary, fontSize: 13, fontWeight: '600', marginBottom: 8 }}>
              Message to Patient (optional)
            </Text>
            <TextInput
              style={{
                color: Colors.textPrimary, fontSize: 14, paddingVertical: 11,
                paddingHorizontal: 14, backgroundColor: Colors.bgInput,
                borderRadius: 12, borderWidth: 1.5, borderColor: Colors.border,
                height: 90, textAlignVertical: 'top',
              }}
              placeholder="e.g. I am monitoring your anemia recovery. Please grant access to your eye scans."
              placeholderTextColor={Colors.textMuted}
              value={message}
              onChangeText={setMessage}
              multiline
              numberOfLines={3}
            />
          </Card>

          {/* Scan type access */}
          <Card style={{ marginBottom: 14 }}>
            <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <Text style={{ color: Colors.textSecondary, fontSize: 13, fontWeight: '600' }}>
                Access to all scan types
              </Text>
              <Switch
                value={allTypes}
                onValueChange={setAllTypes}
                trackColor={{ false: Colors.border, true: `${Colors.primary}80` }}
                thumbColor={allTypes ? Colors.primary : Colors.textMuted}
              />
            </View>

            {!allTypes && (
              <>
                <Text style={{ color: Colors.textMuted, fontSize: 12, marginBottom: 10 }}>
                  Select which scan types you need access to:
                </Text>
                <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
                  {SCAN_MODULES.map(m => {
                    const selected = selectedTypes.includes(m.id);
                    return (
                      <TouchableOpacity
                        key={m.id}
                        onPress={() => toggleType(m.id)}
                        style={{
                          paddingHorizontal: 12, paddingVertical: 8,
                          borderRadius: 10, borderWidth: 1.5,
                          backgroundColor: selected ? `${m.color}20` : Colors.bgInput,
                          borderColor: selected ? m.color : Colors.border,
                          flexDirection: 'row', alignItems: 'center', gap: 5,
                        }}
                      >
                        <Text style={{ fontSize: 14 }}>{m.icon}</Text>
                        <Text style={{
                          color: selected ? m.color : Colors.textSecondary,
                          fontSize: 12, fontWeight: '600',
                        }}>
                          {m.title}
                        </Text>
                      </TouchableOpacity>
                    );
                  })}
                </View>
                {selectedTypes.length === 0 && (
                  <Text style={{ color: Colors.danger, fontSize: 11, marginTop: 8 }}>
                    Please select at least one scan type.
                  </Text>
                )}
              </>
            )}
          </Card>

          {/* Expiry */}
          <Card style={{ marginBottom: 20 }}>
            <Text style={{ color: Colors.textSecondary, fontSize: 13, fontWeight: '600', marginBottom: 8 }}>
              Access Expiry (days)
            </Text>
            <View style={{ flexDirection: 'row', gap: 8 }}>
              {['30', '60', '90', '365'].map(d => (
                <TouchableOpacity
                  key={d}
                  onPress={() => setExpiryDays(d)}
                  style={{
                    flex: 1, paddingVertical: 10, borderRadius: 10, alignItems: 'center',
                    borderWidth: 1.5,
                    backgroundColor: expiryDays === d ? `${Colors.primary}20` : Colors.bgInput,
                    borderColor: expiryDays === d ? Colors.primary : Colors.border,
                  }}
                >
                  <Text style={{
                    color: expiryDays === d ? Colors.primary : Colors.textSecondary,
                    fontSize: 13, fontWeight: '700',
                  }}>
                    {d}d
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
            <Text style={{ color: Colors.textMuted, fontSize: 11, marginTop: 6 }}>
              Patient can revoke access at any time before expiry.
            </Text>
          </Card>

          {/* HIPAA notice */}
          <View style={{
            backgroundColor: `${Colors.info}10`, borderRadius: 12,
            padding: 12, marginBottom: 20,
            borderWidth: 1, borderColor: `${Colors.info}30`,
          }}>
            <Text style={{ color: Colors.info, fontSize: 12, lineHeight: 18 }}>
              🔒 HIPAA Notice: All patient data access is logged and audited.
              Accessing patient data without valid consent is a HIPAA violation.
              The patient retains the right to revoke access at any time.
            </Text>
          </View>

          <Button
            title="Send Consent Request"
            loading={loading}
            onPress={handleSubmit}
            fullWidth
            style={{ opacity: (!allTypes && selectedTypes.length === 0) ? 0.5 : 1 }}
          />
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
