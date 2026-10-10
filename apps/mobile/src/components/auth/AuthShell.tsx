import { ReactNode } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Feather } from '@expo/vector-icons';
import { Colors } from '../../theme/colors';

export default function AuthShell({ title, subtitle, children }: { title: string; subtitle: string; children: ReactNode }) {
  return <SafeAreaView style={{ flex: 1, backgroundColor: Colors.bgDark }}><KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}><ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={{ flexGrow: 1, padding: 24, justifyContent: 'center' }}>
    <View style={{ width: '100%', maxWidth: 440, alignSelf: 'center' }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 32 }}><View style={{ padding: 12, backgroundColor: '#EAF4F0', borderRadius: 14 }}><Feather name="activity" size={26} color={Colors.primary} /></View><Text style={{ color: Colors.textPrimary, fontWeight: '800', fontSize: 23 }}>MediScan <Text style={{ color: Colors.primary }}>AI</Text></Text></View>
      <Text style={{ color: Colors.textPrimary, fontSize: 28, fontWeight: '800', marginBottom: 8 }}>{title}</Text><Text style={{ color: Colors.textSecondary, fontSize: 15, lineHeight: 22, marginBottom: 24 }}>{subtitle}</Text>
      <View style={{ backgroundColor: Colors.white, borderRadius: 20, borderWidth: 1, borderColor: Colors.border, padding: 24 }}>{children}</View>
      <Text style={{ color: Colors.textMuted, fontSize: 11, lineHeight: 17, marginTop: 24, textAlign: 'center' }}>Development preview · Use test data only.{'\n'}Clinical screening is not yet available.</Text>
    </View>
  </ScrollView></KeyboardAvoidingView></SafeAreaView>;
}
