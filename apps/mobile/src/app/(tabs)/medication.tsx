import React, { useState } from 'react';
import {
  View, Text, ScrollView, TextInput, TouchableOpacity, Alert, ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import * as ImagePicker from 'expo-image-picker';
import { Colors } from '../../theme/colors';
import Card from '../../components/common/Card';
import Button from '../../components/common/Button';
import api from '../../services/api';

type InputMode = 'manual' | 'barcode' | 'ocr';

interface DrugInfo {
  drugName: string;
  genericName?: string;
  manufacturer?: string;
  indication?: string;
  sideEffects?: string;
  warnings?: string;
  dosageForm?: string;
  aiAnalysis?: string;
}

export default function MedicationScreen() {
  const [mode, setMode] = useState<InputMode>('manual');
  const [manualInput, setManualInput] = useState('');
  const [drugInfo, setDrugInfo] = useState<DrugInfo | null>(null);
  const [loading, setLoading] = useState(false);

  const searchDrug = async (name: string) => {
    if (!name.trim()) return;
    setLoading(true);
    try {
      const { data } = await api.get<{ success: boolean; data: DrugInfo }>(
        '/medication/search', { params: { q: name } }
      );
      setDrugInfo(data.data);
    } catch {
      Alert.alert('Not Found', `No information found for "${name}". Try a different name.`);
    } finally {
      setLoading(false);
    }
  };

  const handleOcrScan = async () => {
    const result = await ImagePicker.launchCameraAsync({
      quality: 0.9,
      allowsEditing: false,
    });
    if (!result.canceled && result.assets[0]?.uri) {
      Alert.alert('OCR Scan', 'Prescription OCR coming in Phase 4 implementation.');
    }
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: Colors.bgDark }}>
      <ScrollView contentContainerStyle={{ padding: 20 }} showsVerticalScrollIndicator={false}>
        <Text style={{ color: Colors.textPrimary, fontSize: 24, fontWeight: '800', marginBottom: 6 }}>
          💊 Medication Scanner
        </Text>
        <Text style={{ color: Colors.textSecondary, fontSize: 13, marginBottom: 20 }}>
          Search drugs, scan barcode or prescription
        </Text>

        {/* Input mode selector */}
        <View style={{ flexDirection: 'row', gap: 8, marginBottom: 20 }}>
          {([
            { key: 'manual',  label: '⌨️ Type' },
            { key: 'barcode', label: '📷 Barcode' },
            { key: 'ocr',     label: '📄 Prescription' },
          ] as { key: InputMode; label: string }[]).map((m) => (
            <TouchableOpacity
              key={m.key}
              onPress={() => setMode(m.key)}
              style={{
                flex: 1, paddingVertical: 10,
                backgroundColor: mode === m.key ? Colors.primary : Colors.bgCard,
                borderRadius: 12, alignItems: 'center',
                borderWidth: 1, borderColor: mode === m.key ? Colors.primary : Colors.border,
              }}
            >
              <Text style={{
                color: mode === m.key ? Colors.white : Colors.textSecondary,
                fontSize: 12, fontWeight: '600', textAlign: 'center',
              }}>
                {m.label}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Manual input */}
        {mode === 'manual' && (
          <View style={{ marginBottom: 16 }}>
            <View style={{
              flexDirection: 'row',
              backgroundColor: Colors.bgInput,
              borderRadius: 14,
              borderWidth: 1.5,
              borderColor: Colors.border,
              paddingHorizontal: 16,
              alignItems: 'center',
              gap: 10,
            }}>
              <TextInput
                style={{ flex: 1, color: Colors.textPrimary, fontSize: 15, paddingVertical: 14 }}
                placeholder="Drug name, e.g. Paracetamol, Amoxicillin..."
                placeholderTextColor={Colors.textMuted}
                value={manualInput}
                onChangeText={setManualInput}
                onSubmitEditing={() => searchDrug(manualInput)}
                returnKeyType="search"
              />
              {manualInput.length > 0 && (
                <TouchableOpacity onPress={() => setManualInput('')}>
                  <Text style={{ color: Colors.textMuted }}>✕</Text>
                </TouchableOpacity>
              )}
            </View>
            <Button
              title="Search Drug"
              loading={loading}
              onPress={() => searchDrug(manualInput)}
              fullWidth
              style={{ marginTop: 10 }}
            />
          </View>
        )}

        {/* Barcode */}
        {mode === 'barcode' && (
          <Card style={{ alignItems: 'center', paddingVertical: 32, marginBottom: 16 }}>
            <Text style={{ fontSize: 48, marginBottom: 12 }}>📷</Text>
            <Text style={{ color: Colors.textPrimary, fontWeight: '700', fontSize: 16, marginBottom: 8 }}>
              Barcode Scanner
            </Text>
            <Text style={{ color: Colors.textSecondary, fontSize: 13, textAlign: 'center', marginBottom: 20 }}>
              Point camera at medicine barcode or QR code
            </Text>
            <Button
              title="Open Barcode Scanner"
              onPress={() => Alert.alert('Coming Soon', 'Barcode scanner ready in Phase 4')}
            />
          </Card>
        )}

        {/* OCR */}
        {mode === 'ocr' && (
          <Card style={{ alignItems: 'center', paddingVertical: 32, marginBottom: 16 }}>
            <Text style={{ fontSize: 48, marginBottom: 12 }}>📄</Text>
            <Text style={{ color: Colors.textPrimary, fontWeight: '700', fontSize: 16, marginBottom: 8 }}>
              Prescription Scanner
            </Text>
            <Text style={{ color: Colors.textSecondary, fontSize: 13, textAlign: 'center', marginBottom: 20 }}>
              Take a photo of your prescription or medicine box
            </Text>
            <Button title="Scan Prescription" onPress={handleOcrScan} />
          </Card>
        )}

        {/* Drug info result */}
        {loading && (
          <View style={{ alignItems: 'center', paddingVertical: 32 }}>
            <ActivityIndicator color={Colors.primary} size="large" />
            <Text style={{ color: Colors.textSecondary, marginTop: 12 }}>Fetching drug information...</Text>
          </View>
        )}

        {drugInfo && !loading && (
          <View style={{ gap: 12 }}>
            {/* Drug name */}
            <Card>
              <Text style={{ color: Colors.textPrimary, fontSize: 20, fontWeight: '800' }}>
                {drugInfo.drugName}
              </Text>
              {drugInfo.genericName && (
                <Text style={{ color: Colors.textSecondary, fontSize: 14, marginTop: 4 }}>
                  Generic: {drugInfo.genericName}
                </Text>
              )}
              {drugInfo.dosageForm && (
                <View style={{
                  marginTop: 8, alignSelf: 'flex-start',
                  backgroundColor: `${Colors.primary}20`, borderRadius: 8,
                  paddingHorizontal: 10, paddingVertical: 4,
                }}>
                  <Text style={{ color: Colors.primary, fontSize: 12, fontWeight: '600' }}>
                    {drugInfo.dosageForm}
                  </Text>
                </View>
              )}
            </Card>

            {drugInfo.indication && (
              <Card>
                <Text style={{ color: Colors.success, fontWeight: '700', marginBottom: 6 }}>✅ Used For</Text>
                <Text style={{ color: Colors.textSecondary, fontSize: 13, lineHeight: 20 }}>
                  {drugInfo.indication}
                </Text>
              </Card>
            )}

            {drugInfo.sideEffects && (
              <Card>
                <Text style={{ color: Colors.warning, fontWeight: '700', marginBottom: 6 }}>⚠️ Side Effects</Text>
                <Text style={{ color: Colors.textSecondary, fontSize: 13, lineHeight: 20 }}>
                  {drugInfo.sideEffects}
                </Text>
              </Card>
            )}

            {drugInfo.warnings && (
              <Card style={{ borderColor: `${Colors.danger}40` }}>
                <Text style={{ color: Colors.danger, fontWeight: '700', marginBottom: 6 }}>🚫 Warnings</Text>
                <Text style={{ color: Colors.textSecondary, fontSize: 13, lineHeight: 20 }}>
                  {drugInfo.warnings}
                </Text>
              </Card>
            )}

            {/* AI analysis */}
            {drugInfo.aiAnalysis && (
              <Card>
                <Text style={{ color: Colors.primary, fontWeight: '700', marginBottom: 6 }}>🤖 AI Analysis</Text>
                <Text style={{ color: Colors.textSecondary, fontSize: 13, lineHeight: 20 }}>
                  {drugInfo.aiAnalysis}
                </Text>
              </Card>
            )}

            {/* Disclaimer */}
            <View style={{
              backgroundColor: `${Colors.warning}10`, borderRadius: 12,
              padding: 12, borderWidth: 1, borderColor: `${Colors.warning}30`,
            }}>
              <Text style={{ color: Colors.warning, fontSize: 12, lineHeight: 17 }}>
                ⚕️ Drug information is fetched from OpenFDA and Pakistan DAP. Always follow your doctor's prescription. Never self-medicate.
              </Text>
            </View>
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}
