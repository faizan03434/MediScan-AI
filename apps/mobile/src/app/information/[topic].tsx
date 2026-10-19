import { ScrollView, Text, TouchableOpacity, View } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Colors } from '../../theme/colors';

const content = {
  privacy: { title: 'Privacy & your data', sections: [
    ['Development environment', 'This preview uses a local database, private authenticated photo endpoints and HTTP over your Wi-Fi. Use test data. Profile > My Data & Sessions provides record export and all-device sign out. Permanent erasure and backup handling depend on the server retention policy; production deployment remains pending.'],
    ['Photo consent', 'Each health capture asks before upload. Only upload photos you are allowed to use. Saved records and photos belong to your signed-in account. Removing a record hides it; permanent file erasure is not implemented yet.'],
    ['Doctor access', 'Manage doctor access requests from Profile. Access must be granted through the consent workflow; an ordinary user cannot open the doctor portal.'],
    ['Account activity', 'Open Account Activity from Profile to review recorded actions through your account, including scan reads and changes. This development log is not yet a complete production security audit.'],
    ['Clinical and compliance status', 'The workflows store photos, including uploaded fundus images. They do not yet diagnose illness, assess healing, verify prescriptions or provide medical treatment. No HIPAA certification or regulatory approval is claimed.'],
  ] },
  help: { title: 'Help & support', sections: [
    ['Open on iPhone', 'Install Expo Go, connect your phone and computer to the same Wi-Fi, scan the preview QR with the iPhone Camera, then tap Open in Expo Go. The API and Metro servers must remain running.'],
    ['Email verification', 'Registration and password reset use a six-digit email code. Codes last 10 minutes. Wait 60 seconds before resending; check spam. Email delivery needs the server SMTP app password.'],
    ['Google sign-in', 'Google OAuth client IDs must be configured first. iPhone Google sign-in needs a MediScan development build. Email sign-in works in Expo Go.'],
    ['Medicine records', 'OpenFDA information is a US reference source. It does not confirm Pakistan registration or a correct prescription. Confirm the exact ingredient, strength and form with a pharmacist; an unknown barcode needs manual entry.'],
    ['Photo results', 'Inconclusive means no clinical assessment was made. Photos and comparisons cannot confirm recovery or replace a clinical examination. For persistent or worsening symptoms, seek a qualified clinician.'],
  ] },
};
export default function InformationScreen() {
  const router = useRouter(); const { topic } = useLocalSearchParams<{ topic: string }>();
  const page = topic === 'privacy' ? content.privacy : content.help;
  return <SafeAreaView style={{ flex: 1, backgroundColor: Colors.bgDark }}><ScrollView contentContainerStyle={{ padding: 24 }}><View style={{ width: '100%', maxWidth: 680, alignSelf: 'center' }}><TouchableOpacity onPress={() => router.back()}><Text style={{ color: Colors.primary, marginBottom: 24 }}>← Back</Text></TouchableOpacity><Text style={{ color: Colors.textPrimary, fontWeight: '800', fontSize: 28, marginBottom: 24 }}>{page.title}</Text>{page.sections.map(([title, body]) => <View key={title} style={{ backgroundColor: Colors.white, padding: 20, borderRadius: 16, borderWidth: 1, borderColor: Colors.border, marginBottom: 14 }}><Text style={{ color: Colors.textPrimary, fontWeight: '700', fontSize: 17, marginBottom: 8 }}>{title}</Text><Text style={{ color: Colors.textSecondary, lineHeight: 23 }}>{body}</Text></View>)}</View></ScrollView></SafeAreaView>;
}
