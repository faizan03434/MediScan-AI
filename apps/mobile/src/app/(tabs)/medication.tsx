import React, { useState, useEffect, useRef } from 'react';
import {
  View, Text, ScrollView, TextInput, TouchableOpacity,
  Alert, ActivityIndicator, Modal, KeyboardAvoidingView,
  Platform, FlatList,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { CameraView, useCameraPermissions } from 'expo-camera';
import * as ImagePicker from 'expo-image-picker';
import { LinearGradient } from 'expo-linear-gradient';
import { useQuery } from '@tanstack/react-query';
import useMedicationStore from '../../store/medicationStore';
import medicationService from '../../services/medicationService';
import Card from '../../components/common/Card';
import Button from '../../components/common/Button';
import { Colors } from '../../theme/colors';
import type { DrugInfo } from '../../services/medicationService';
import { format } from 'date-fns';

type InputMode = 'manual' | 'barcode' | 'prescription';
type ViewState = 'input' | 'scanning' | 'loading' | 'result' | 'prescription_result';

export default function MedicationScreen() {
  const router = useRouter();
  const [mode, setMode] = useState<InputMode>('manual');
  const [viewState, setViewState] = useState<ViewState>('input');
  const [manualQuery, setManualQuery] = useState('');
  const [doctorName, setDoctorName] = useState('');
  const [prescriptionNotes, setPrescriptionNotes] = useState('');
  const [scannedBarcode, setScannedBarcode] = useState('');
  const [isBarcodeScanned, setIsBarcodeScanned] = useState(false);

  const [cameraPermission, requestCameraPermission] = useCameraPermissions();

  const {
    currentDrug, currentPrescription, isLoading, error,
    searchByName, searchByBarcode, analyzePrescription, clearCurrent,
  } = useMedicationStore();

  const { data: history, refetch: refetchHistory } = useQuery({
    queryKey: ['medicationHistory'],
    queryFn: () => medicationService.getHistory(1, 5),
    staleTime: 60_000,
  });

  // ── Manual search ─────────────────────────────────────────
  const handleManualSearch = async () => {
    if (manualQuery.trim().length < 2) {
      Alert.alert('Too short', 'Enter at least 2 characters to search.');
      return;
    }
    setViewState('loading');
    try {
      await searchByName(manualQuery.trim());
      setViewState('result');
    } catch {
      setViewState('input');
      Alert.alert('Not Found', `No information found for "${manualQuery}".`);
    }
  };

  // ── Barcode scan result ───────────────────────────────────
  const handleBarcodeScan = async ({ data }: { data: string }) => {
    if (isBarcodeScanned) return;
    setIsBarcodeScanned(true);
    setScannedBarcode(data);
    setViewState('loading');
    try {
      await searchByBarcode(data);
      setViewState('result');
    } catch {
      setViewState('input');
      setIsBarcodeScanned(false);
      Alert.alert('Not Found', `Barcode "${data}" not found in drug database.`);
    }
  };

  // ── Prescription OCR ──────────────────────────────────────
  const handlePrescriptionCapture = async () => {
    const result = await ImagePicker.launchCameraAsync({
      quality: 0.9,
      allowsEditing: false,
    });

    if (result.canceled || !result.assets[0]?.uri) return;
    const uri = result.assets[0].uri;

    if (!prescriptionNotes.trim() && !doctorName.trim()) {
      Alert.alert(
        'Tip for Better Results',
        'Type the drug names (one per line) in the Notes field below for more accurate analysis. Or continue without it.',
        [
          { text: 'Add Notes', style: 'cancel' },
          {
            text: 'Continue',
            onPress: () => runPrescriptionAnalysis(uri),
          },
        ],
      );
    } else {
      await runPrescriptionAnalysis(uri);
    }
  };

  const runPrescriptionAnalysis = async (uri: string) => {
    setViewState('loading');
    try {
      await analyzePrescription(uri, doctorName, prescriptionNotes);
      setViewState('prescription_result');
      refetchHistory();
    } catch {
      setViewState('input');
      Alert.alert('Analysis Failed', 'Could not analyze prescription. Please try again.');
    }
  };

  const handleReset = () => {
    clearCurrent();
    setViewState('input');
    setManualQuery('');
    setScannedBarcode('');
    setIsBarcodeScanned(false);
    setDoctorName('');
    setPrescriptionNotes('');
  };

  // ── Loading state ─────────────────────────────────────────
  if (viewState === 'loading') {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: Colors.bgDark, justifyContent: 'center', alignItems: 'center' }}>
        <ActivityIndicator size="large" color={Colors.primary} />
        <Text style={{ color: Colors.textSecondary, marginTop: 16, fontSize: 16 }}>
          {mode === 'prescription' ? 'Analyzing prescription with AI...' : 'Fetching drug information...'}
        </Text>
        <Text style={{ color: Colors.textMuted, marginTop: 8, fontSize: 13 }}>
          {mode === 'prescription' ? 'This may take 15-30 seconds' : 'Checking OpenFDA database...'}
        </Text>
      </SafeAreaView>
    );
  }

  // ── Barcode camera view ───────────────────────────────────
  if (viewState === 'scanning') {
    if (!cameraPermission?.granted) {
      return (
        <SafeAreaView style={{ flex: 1, backgroundColor: Colors.bgDark, justifyContent: 'center', alignItems: 'center', padding: 24 }}>
          <Text style={{ color: Colors.textPrimary, fontSize: 18, fontWeight: '700', marginBottom: 12, textAlign: 'center' }}>
            Camera Permission Required
          </Text>
          <Button title="Grant Permission" onPress={requestCameraPermission} />
          <Button title="Cancel" variant="ghost" onPress={() => setViewState('input')} style={{ marginTop: 8 }} />
        </SafeAreaView>
      );
    }

    return (
      <View style={{ flex: 1, backgroundColor: Colors.bgDark }}>
        <CameraView
          style={{ flex: 1 }}
          facing="back"
          onBarcodeScanned={isBarcodeScanned ? undefined : handleBarcodeScan}
          barcodeScannerSettings={{ barcodeTypes: ['ean13', 'ean8', 'qr', 'code128', 'upc_a'] }}
        >
          {/* Top bar */}
          <View style={{ paddingTop: 52, paddingHorizontal: 16, paddingBottom: 16, backgroundColor: 'rgba(0,0,0,0.6)' }}>
            <TouchableOpacity onPress={() => setViewState('input')}>
              <Text style={{ color: Colors.white, fontSize: 15 }}>✕ Cancel</Text>
            </TouchableOpacity>
          </View>

          {/* Scan frame */}
          <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
            <View style={{
              width: 280, height: 160,
              borderWidth: 2, borderColor: Colors.primary,
              borderRadius: 12,
            }}>
              {/* Corner markers */}
              {[
                { top: -2, left: -2, borderTopWidth: 4, borderLeftWidth: 4 },
                { top: -2, right: -2, borderTopWidth: 4, borderRightWidth: 4 },
                { bottom: -2, left: -2, borderBottomWidth: 4, borderLeftWidth: 4 },
                { bottom: -2, right: -2, borderBottomWidth: 4, borderRightWidth: 4 },
              ].map((style, i) => (
                <View key={i} style={[{
                  position: 'absolute', width: 24, height: 24,
                  borderColor: Colors.primary,
                }, style]} />
              ))}
              {/* Scan line animation placeholder */}
              <View style={{
                position: 'absolute', left: 0, right: 0, top: '50%',
                height: 2, backgroundColor: `${Colors.primary}80`,
              }} />
            </View>
            <Text style={{
              color: 'rgba(255,255,255,0.9)', marginTop: 20,
              fontSize: 14, textAlign: 'center',
              backgroundColor: 'rgba(0,0,0,0.5)', paddingHorizontal: 16, paddingVertical: 8, borderRadius: 8,
            }}>
              Point camera at barcode or QR code on medicine packaging
            </Text>
          </View>

          {/* Bottom hint */}
          <View style={{ padding: 24, backgroundColor: 'rgba(0,0,0,0.6)' }}>
            <Text style={{ color: Colors.textMuted, fontSize: 12, textAlign: 'center' }}>
              Supported: EAN-13, EAN-8, QR Code, Code-128, UPC-A
            </Text>
          </View>
        </CameraView>
      </View>
    );
  }

  // ── Drug result view ──────────────────────────────────────
  if (viewState === 'result' && currentDrug) {
    return <DrugResultView drug={currentDrug} onBack={handleReset} onSave={() => {
      Alert.alert('Saved', 'Drug added to your medication history.');
      refetchHistory();
    }} />;
  }

  // ── Prescription result view ──────────────────────────────
  if (viewState === 'prescription_result' && currentPrescription) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: Colors.bgDark }}>
        <ScrollView contentContainerStyle={{ padding: 20 }} showsVerticalScrollIndicator={false}>
          <TouchableOpacity onPress={handleReset} style={{ marginBottom: 16 }}>
            <Text style={{ color: Colors.primary }}>← Back</Text>
          </TouchableOpacity>

          <Text style={{ color: Colors.textPrimary, fontSize: 22, fontWeight: '800', marginBottom: 4 }}>
            📄 Prescription Analysis
          </Text>
          {currentPrescription.doctorName && (
            <Text style={{ color: Colors.textSecondary, fontSize: 14, marginBottom: 16 }}>
              Dr. {currentPrescription.doctorName}
            </Text>
          )}

          {/* Safety warning banner */}
          {currentPrescription.hasSafetyWarnings && (
            <View style={{ backgroundColor: `${Colors.danger}15`, borderRadius: 12, padding: 12, marginBottom: 12, borderWidth: 1, borderColor: `${Colors.danger}40` }}>
              <Text style={{ color: Colors.danger, fontWeight: '700', marginBottom: 4 }}>⚠️ Safety Warning Detected</Text>
              <Text style={{ color: Colors.textSecondary, fontSize: 13 }}>
                This prescription has potential drug interactions or warnings. Consult your doctor.
              </Text>
            </View>
          )}

          {/* AI Analysis */}
          {currentPrescription.aiAnalysis && (
            <Card style={{ marginBottom: 12 }}>
              <Text style={{ color: Colors.primary, fontWeight: '700', marginBottom: 6 }}>🤖 AI Safety Analysis</Text>
              <Text style={{ color: Colors.textSecondary, fontSize: 13, lineHeight: 20 }}>
                {currentPrescription.aiAnalysis}
              </Text>
            </Card>
          )}

          {/* Interactions */}
          {currentPrescription.interactions.length > 0 && (
            <Card style={{ marginBottom: 12, borderColor: `${Colors.warning}40` }}>
              <Text style={{ color: Colors.warning, fontWeight: '700', marginBottom: 8 }}>⚡ Drug Interactions</Text>
              {currentPrescription.interactions.map((item, i) => (
                <Text key={i} style={{ color: Colors.textSecondary, fontSize: 13, marginBottom: 4 }}>• {item}</Text>
              ))}
            </Card>
          )}

          {/* Medications list */}
          <Text style={{ color: Colors.textPrimary, fontWeight: '700', fontSize: 16, marginBottom: 10 }}>
            Medications Found ({currentPrescription.medications.length})
          </Text>
          {currentPrescription.medications.map((med, i) => (
            <Card key={i} padding={12} style={{ marginBottom: 8 }}>
              <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
                <Text style={{ color: Colors.textPrimary, fontWeight: '700', fontSize: 15 }}>{med.drugName}</Text>
                <View style={{
                  backgroundColor: med.isKnownDrug ? `${Colors.success}20` : `${Colors.warning}20`,
                  borderRadius: 8, paddingHorizontal: 8, paddingVertical: 3,
                }}>
                  <Text style={{ fontSize: 11, fontWeight: '700', color: med.isKnownDrug ? Colors.success : Colors.warning }}>
                    {med.isKnownDrug ? 'Verified ✓' : 'Unknown'}
                  </Text>
                </View>
              </View>
              {med.drugInfo?.indication && (
                <Text style={{ color: Colors.textMuted, fontSize: 12, marginTop: 4 }} numberOfLines={2}>
                  {med.drugInfo.indication}
                </Text>
              )}
            </Card>
          ))}

          {/* Disclaimer */}
          <View style={{ backgroundColor: `${Colors.warning}10`, borderRadius: 12, padding: 12, marginTop: 8, marginBottom: 20, borderWidth: 1, borderColor: `${Colors.warning}30` }}>
            <Text style={{ color: Colors.warning, fontSize: 11, lineHeight: 17 }}>
              ⚕️ {currentPrescription.disclaimer}
            </Text>
          </View>

          <Button title="Done" onPress={handleReset} fullWidth />
        </ScrollView>
      </SafeAreaView>
    );
  }

  // ── Main input view ───────────────────────────────────────
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: Colors.bgDark }}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
        <ScrollView
          contentContainerStyle={{ padding: 20, paddingBottom: 40 }}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          {/* Header */}
          <LinearGradient
            colors={['#1E293B', '#0F172A']}
            style={{ borderRadius: 20, padding: 20, marginBottom: 20 }}
          >
            <Text style={{ color: Colors.textPrimary, fontSize: 24, fontWeight: '800' }}>
              💊 Medication Scanner
            </Text>
            <Text style={{ color: Colors.textSecondary, fontSize: 13, marginTop: 4 }}>
              Search drugs, scan barcode, or analyze prescription
            </Text>
          </LinearGradient>

          {/* Mode selector */}
          <View style={{ flexDirection: 'row', gap: 8, marginBottom: 20 }}>
            {([
              { key: 'manual', icon: '⌨️', label: 'Search' },
              { key: 'barcode', icon: '📷', label: 'Barcode' },
              { key: 'prescription', icon: '📄', label: 'Prescription' },
            ] as { key: InputMode; icon: string; label: string }[]).map((m) => (
              <TouchableOpacity
                key={m.key}
                onPress={() => setMode(m.key)}
                style={{
                  flex: 1, paddingVertical: 12,
                  backgroundColor: mode === m.key ? Colors.primary : Colors.bgCard,
                  borderRadius: 14, alignItems: 'center',
                  borderWidth: 1.5,
                  borderColor: mode === m.key ? Colors.primary : Colors.border,
                }}
              >
                <Text style={{ fontSize: 18 }}>{m.icon}</Text>
                <Text style={{
                  color: mode === m.key ? Colors.white : Colors.textSecondary,
                  fontSize: 12, fontWeight: '600', marginTop: 3,
                }}>
                  {m.label}
                </Text>
              </TouchableOpacity>
            ))}
          </View>

          {/* Manual search */}
          {mode === 'manual' && (
            <Card style={{ marginBottom: 16 }}>
              <Text style={{ color: Colors.textSecondary, fontSize: 13, fontWeight: '600', marginBottom: 8 }}>
                Drug Name
              </Text>
              <View style={{
                flexDirection: 'row', backgroundColor: Colors.bgInput,
                borderRadius: 12, borderWidth: 1.5, borderColor: Colors.border,
                paddingHorizontal: 14, alignItems: 'center', gap: 10,
              }}>
                <TextInput
                  style={{ flex: 1, color: Colors.textPrimary, fontSize: 15, paddingVertical: 13 }}
                  placeholder="e.g. Paracetamol, Amoxicillin, Brufen..."
                  placeholderTextColor={Colors.textMuted}
                  value={manualQuery}
                  onChangeText={setManualQuery}
                  onSubmitEditing={handleManualSearch}
                  returnKeyType="search"
                  autoCapitalize="none"
                />
                {manualQuery.length > 0 && (
                  <TouchableOpacity onPress={() => setManualQuery('')}>
                    <Text style={{ color: Colors.textMuted, fontSize: 16 }}>✕</Text>
                  </TouchableOpacity>
                )}
              </View>
              <Text style={{ color: Colors.textMuted, fontSize: 11, marginTop: 6 }}>
                Searches OpenFDA database + Pakistan drug registry
              </Text>
              <Button
                title="Search Drug"
                loading={isLoading}
                onPress={handleManualSearch}
                fullWidth
                style={{ marginTop: 14 }}
              />
            </Card>
          )}

          {/* Barcode */}
          {mode === 'barcode' && (
            <Card style={{ marginBottom: 16, alignItems: 'center' }}>
              <Text style={{ fontSize: 48, marginBottom: 12 }}>📷</Text>
              <Text style={{ color: Colors.textPrimary, fontWeight: '700', fontSize: 17, marginBottom: 6 }}>
                Scan Medicine Barcode
              </Text>
              <Text style={{ color: Colors.textSecondary, fontSize: 13, textAlign: 'center', marginBottom: 8, lineHeight: 19 }}>
                Point camera at the barcode on the medicine box, strip, or bottle.
              </Text>
              <Text style={{ color: Colors.textMuted, fontSize: 12, textAlign: 'center', marginBottom: 20 }}>
                Supports EAN-13 • EAN-8 • QR Code • UPC-A
              </Text>
              <Button
                title="Open Barcode Scanner"
                onPress={() => {
                  setIsBarcodeScanned(false);
                  setViewState('scanning');
                }}
                fullWidth
              />
              {/* Manual barcode entry fallback */}
              <View style={{ width: '100%', marginTop: 16 }}>
                <Text style={{ color: Colors.textMuted, fontSize: 12, textAlign: 'center', marginBottom: 8 }}>
                  Or type barcode manually:
                </Text>
                <View style={{
                  flexDirection: 'row', gap: 8, alignItems: 'center',
                }}>
                  <TextInput
                    style={{
                      flex: 1, color: Colors.textPrimary, fontSize: 14, paddingVertical: 10,
                      paddingHorizontal: 12, backgroundColor: Colors.bgInput,
                      borderRadius: 10, borderWidth: 1, borderColor: Colors.border,
                    }}
                    placeholder="Type barcode number..."
                    placeholderTextColor={Colors.textMuted}
                    value={scannedBarcode}
                    onChangeText={setScannedBarcode}
                    keyboardType="numeric"
                  />
                  <TouchableOpacity
                    onPress={async () => {
                      if (!scannedBarcode.trim()) return;
                      setViewState('loading');
                      try {
                        await searchByBarcode(scannedBarcode.trim());
                        setViewState('result');
                      } catch {
                        setViewState('input');
                        Alert.alert('Not Found', 'Barcode not found in drug database.');
                      }
                    }}
                    style={{
                      backgroundColor: Colors.primary, borderRadius: 10,
                      paddingHorizontal: 14, paddingVertical: 11,
                    }}
                  >
                    <Text style={{ color: Colors.white, fontWeight: '700' }}>Go</Text>
                  </TouchableOpacity>
                </View>
              </View>
            </Card>
          )}

          {/* Prescription */}
          {mode === 'prescription' && (
            <Card style={{ marginBottom: 16 }}>
              <Text style={{ color: Colors.textPrimary, fontWeight: '700', fontSize: 16, marginBottom: 14 }}>
                📄 Prescription Scanner
              </Text>

              {/* Doctor name */}
              <View style={{ marginBottom: 12 }}>
                <Text style={{ color: Colors.textSecondary, fontSize: 13, fontWeight: '600', marginBottom: 6 }}>
                  Doctor Name (optional)
                </Text>
                <TextInput
                  style={{
                    color: Colors.textPrimary, fontSize: 14, paddingVertical: 11,
                    paddingHorizontal: 14, backgroundColor: Colors.bgInput,
                    borderRadius: 12, borderWidth: 1.5, borderColor: Colors.border,
                  }}
                  placeholder="Dr. Ali Hassan..."
                  placeholderTextColor={Colors.textMuted}
                  value={doctorName}
                  onChangeText={setDoctorName}
                />
              </View>

              {/* Drug names / notes */}
              <View style={{ marginBottom: 16 }}>
                <Text style={{ color: Colors.textSecondary, fontSize: 13, fontWeight: '600', marginBottom: 6 }}>
                  Drug Names — one per line (for better accuracy)
                </Text>
                <TextInput
                  style={{
                    color: Colors.textPrimary, fontSize: 14, paddingVertical: 11,
                    paddingHorizontal: 14, backgroundColor: Colors.bgInput,
                    borderRadius: 12, borderWidth: 1.5, borderColor: Colors.border,
                    height: 100, textAlignVertical: 'top',
                  }}
                  placeholder={"Paracetamol 500mg\nAmoxicillin 250mg\nOmeprazole..."}
                  placeholderTextColor={Colors.textMuted}
                  value={prescriptionNotes}
                  onChangeText={setPrescriptionNotes}
                  multiline
                  numberOfLines={4}
                />
              </View>

              <Text style={{ color: Colors.textMuted, fontSize: 12, lineHeight: 17, marginBottom: 16 }}>
                📌 Tip: Type drug names above for best results. Photo helps doctor name detection. AI will analyze drug interactions and safety.
              </Text>

              <Button
                title="📷 Take Prescription Photo"
                onPress={handlePrescriptionCapture}
                fullWidth
              />
              <Button
                title="🖼️ Choose from Gallery"
                variant="outline"
                onPress={async () => {
                  const result = await ImagePicker.launchImageLibraryAsync({ quality: 0.9 });
                  if (!result.canceled && result.assets[0]?.uri) {
                    await runPrescriptionAnalysis(result.assets[0].uri);
                  }
                }}
                fullWidth
                style={{ marginTop: 8 }}
              />
            </Card>
          )}

          {/* Recent medication history */}
          {history && history.items.length > 0 && (
            <View style={{ marginTop: 8 }}>
              <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <Text style={{ color: Colors.textPrimary, fontWeight: '700', fontSize: 16 }}>
                  Recent Medications
                </Text>
              </View>
              {history.items.slice(0, 4).map((item) => (
                <TouchableOpacity
                  key={item.id}
                  activeOpacity={0.8}
                  onPress={() => {
                    setManualQuery(item.drugName);
                    setMode('manual');
                  }}
                >
                  <Card padding={12} style={{ marginBottom: 8 }}>
                    <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <View style={{ flex: 1 }}>
                        <Text style={{ color: Colors.textPrimary, fontWeight: '700', fontSize: 14 }}>
                          {item.drugName}
                        </Text>
                        {item.genericName && (
                          <Text style={{ color: Colors.textMuted, fontSize: 12 }}>
                            Generic: {item.genericName}
                          </Text>
                        )}
                        {item.indication && (
                          <Text style={{ color: Colors.textSecondary, fontSize: 12, marginTop: 2 }} numberOfLines={1}>
                            {item.indication}
                          </Text>
                        )}
                      </View>
                      <View style={{ alignItems: 'flex-end', gap: 4 }}>
                        <Text style={{ color: Colors.textMuted, fontSize: 11 }}>
                          {format(new Date(item.createdAt), 'MMM d')}
                        </Text>
                        {item.hasSafetyWarning && (
                          <Text style={{ color: Colors.danger, fontSize: 11, fontWeight: '700' }}>⚠️ Warning</Text>
                        )}
                      </View>
                    </View>
                  </Card>
                </TouchableOpacity>
              ))}
            </View>
          )}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

// ── Drug result component ─────────────────────────────────────
function DrugResultView({
  drug, onBack, onSave,
}: { drug: DrugInfo; onBack: () => void; onSave: () => void }) {
  const isSaved = React.useRef(false);

  const handleSave = async () => {
    if (isSaved.current) return;
    isSaved.current = true;
    try {
      await medicationService.saveMedication({
        drugName: drug.brandName,
        genericName: drug.genericName,
        dosageForm: drug.dosageForm,
        strength: drug.strength,
        inputMethod: 'ManualEntry',
      });
      onSave();
    } catch { /* silent */ }
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: Colors.bgDark }}>
      <ScrollView contentContainerStyle={{ padding: 20, paddingBottom: 32 }} showsVerticalScrollIndicator={false}>
        <TouchableOpacity onPress={onBack} style={{ marginBottom: 16 }}>
          <Text style={{ color: Colors.primary }}>← Back</Text>
        </TouchableOpacity>

        {/* Drug header */}
        <Card style={{ marginBottom: 12 }}>
          <Text style={{ color: Colors.textPrimary, fontSize: 22, fontWeight: '800' }}>
            {drug.brandName}
          </Text>
          {drug.genericName && (
            <Text style={{ color: Colors.textSecondary, fontSize: 14, marginTop: 2 }}>
              Generic: {drug.genericName}
            </Text>
          )}
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 10 }}>
            {drug.dosageForm && (
              <View style={{ backgroundColor: `${Colors.primary}20`, borderRadius: 8, paddingHorizontal: 10, paddingVertical: 4 }}>
                <Text style={{ color: Colors.primary, fontSize: 12, fontWeight: '600' }}>{drug.dosageForm}</Text>
              </View>
            )}
            {drug.strength && (
              <View style={{ backgroundColor: `${Colors.secondary}20`, borderRadius: 8, paddingHorizontal: 10, paddingVertical: 4 }}>
                <Text style={{ color: Colors.secondary, fontSize: 12, fontWeight: '600' }}>{drug.strength}</Text>
              </View>
            )}
            {drug.source && (
              <View style={{ backgroundColor: `${Colors.success}20`, borderRadius: 8, paddingHorizontal: 10, paddingVertical: 4 }}>
                <Text style={{ color: Colors.success, fontSize: 12, fontWeight: '600' }}>📡 {drug.source}</Text>
              </View>
            )}
          </View>
        </Card>

        {/* Indication */}
        {drug.indication && (
          <Card style={{ marginBottom: 10 }}>
            <Text style={{ color: Colors.success, fontWeight: '700', marginBottom: 6 }}>✅ Used For</Text>
            <Text style={{ color: Colors.textSecondary, fontSize: 13, lineHeight: 20 }}>{drug.indication}</Text>
          </Card>
        )}

        {/* AI Analysis */}
        {drug.aiAnalysis && (
          <Card style={{ marginBottom: 10 }}>
            <Text style={{ color: Colors.primary, fontWeight: '700', marginBottom: 6 }}>🤖 AI Summary</Text>
            <Text style={{ color: Colors.textSecondary, fontSize: 13, lineHeight: 20 }}>{drug.aiAnalysis}</Text>
          </Card>
        )}

        {/* Side effects */}
        {drug.sideEffects.length > 0 && (
          <Card style={{ marginBottom: 10 }}>
            <Text style={{ color: Colors.warning, fontWeight: '700', marginBottom: 8 }}>⚠️ Side Effects</Text>
            {drug.sideEffects.slice(0, 5).map((s, i) => (
              <Text key={i} style={{ color: Colors.textSecondary, fontSize: 13, marginBottom: 4 }}>• {s}</Text>
            ))}
          </Card>
        )}

        {/* Warnings */}
        {drug.warnings.length > 0 && (
          <Card style={{ marginBottom: 10, borderColor: `${Colors.danger}40` }}>
            <Text style={{ color: Colors.danger, fontWeight: '700', marginBottom: 8 }}>🚫 Warnings</Text>
            {drug.warnings.slice(0, 4).map((w, i) => (
              <Text key={i} style={{ color: Colors.textSecondary, fontSize: 13, marginBottom: 4 }}>• {w}</Text>
            ))}
          </Card>
        )}

        {/* Interactions */}
        {drug.interactions.length > 0 && (
          <Card style={{ marginBottom: 10 }}>
            <Text style={{ color: Colors.warning, fontWeight: '700', marginBottom: 8 }}>⚡ Drug Interactions</Text>
            {drug.interactions.slice(0, 3).map((d, i) => (
              <Text key={i} style={{ color: Colors.textSecondary, fontSize: 13, marginBottom: 4 }}>• {d}</Text>
            ))}
          </Card>
        )}

        {/* Storage */}
        {drug.storageInfo && (
          <Card style={{ marginBottom: 10 }}>
            <Text style={{ color: Colors.info, fontWeight: '700', marginBottom: 6 }}>📦 Storage</Text>
            <Text style={{ color: Colors.textSecondary, fontSize: 13 }}>{drug.storageInfo}</Text>
          </Card>
        )}

        {/* Disclaimer */}
        <View style={{ backgroundColor: `${Colors.warning}10`, borderRadius: 12, padding: 12, marginBottom: 20, borderWidth: 1, borderColor: `${Colors.warning}30` }}>
          <Text style={{ color: Colors.warning, fontSize: 11, lineHeight: 17 }}>⚕️ {drug.disclaimer}</Text>
        </View>

        {/* Actions */}
        <View style={{ gap: 10 }}>
          <Button title="💾 Save to History" onPress={handleSave} fullWidth />
          <Button title="Search Another Drug" variant="outline" onPress={onBack} fullWidth />
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}
