import React, { useState } from 'react';
import { View, Text, TextInput, Image, Switch } from 'react-native';
import Button from './Button';
import { Colors } from '../../theme/colors';
import { extractDocument } from '../../services/documentService';
import { errorMessage } from '../../utils/errorMessage';

export default function DocumentReview({ uri, initialNames, box, onConfirm, onCancel }: {
  uri: string; initialNames: string; box: boolean;
  onConfirm: (names: string, rawText: string, fromOcr: boolean) => Promise<void>;
  onCancel: () => void;
}) {
  const [raw, setRaw] = useState('');
  const [names, setNames] = useState(initialNames);
  const [confirmed, setConfirmed] = useState(false);
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [extracted, setExtracted] = useState(false);
  const [message, setMessage] = useState('');
  const read = async () => {
    setBusy(true); setMessage(''); setConfirmed(false);
    try {
      const result = await extractDocument(uri);
      setRaw(result.text); setExtracted(true);
      setMessage(result.message || 'Check every extracted line against the photo.');
    } catch (error) { setMessage(errorMessage(error)); }
    finally { setBusy(false); }
  };
  const submit = async () => {
    setBusy(true); setMessage('');
    try { await onConfirm(names.trim(), raw, extracted); }
    catch (error) { setMessage(errorMessage(error)); }
    finally { setBusy(false); }
  };
  return <View style={{ gap: 14 }}>
    <Text style={{ color: Colors.textPrimary, fontSize: 22, fontWeight: '700' }}>Review your photo</Text>
    <Image source={{ uri }} style={{ width: '100%', height: 230, borderRadius: 12 }} resizeMode="contain" />
    <Text style={{ color: Colors.textSecondary, lineHeight: 21 }}>Printed English text is supported. Handwriting and medicine identity are not verified. Check names, strength and form yourself.</Text>
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
      <Switch accessibilityLabel="Photo processing consent" value={consent} onValueChange={setConsent} />
      <Text style={{ flex: 1, color: Colors.textSecondary }}>I agree to process this photo on the MediScan server{box ? '.' : ' and save it privately with my prescription record.'}</Text>
    </View>
    <Button title="Extract text from photo" onPress={read} disabled={!consent || busy} loading={busy} />
    {!!message && <Text accessibilityRole="alert" style={{ color: Colors.textSecondary, lineHeight: 21 }}>{message}</Text>}
    {!!raw && <View style={{ gap: 8 }}><Text style={{ color: Colors.textPrimary, fontWeight: '600' }}>Extracted text — check against photo</Text><Text selectable style={{ color: Colors.textSecondary, lineHeight: 22 }}>{raw}</Text></View>}
    <Text style={{ color: Colors.textPrimary, fontWeight: '600' }}>{box ? 'Exact medicine name for lookup' : 'Confirmed medicine names — one per line'}</Text>
    <TextInput accessibilityLabel="Confirmed medicine names" value={names} onChangeText={value => { setNames(value); setConfirmed(false); }} multiline={!box} maxLength={5000} placeholder={box ? 'Type the exact brand or generic name' : 'Type only medicine names, one per line'} style={{ color: Colors.textPrimary, borderWidth: 1, borderColor: Colors.border, borderRadius: 12, padding: 14, minHeight: box ? 52 : 110 }} />
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}><Switch accessibilityLabel="Confirm medicine details" value={confirmed} onValueChange={setConfirmed} /><Text style={{ flex: 1, color: Colors.textSecondary }}>I checked these names, strength and form against the original photo.</Text></View>
    <Text style={{ color: Colors.textMuted, lineHeight: 19 }}>A label match does not verify this prescription, its dose, interactions or Pakistan registration. Ask your doctor or pharmacist before taking medicine.</Text>
    <Button title={box ? 'Look up confirmed name' : 'Save and look up confirmed medicines'} onPress={submit} disabled={!consent || !confirmed || !names.trim() || busy} />
    <Button title="Cancel" variant="outline" onPress={onCancel} disabled={busy} />
  </View>;
}
