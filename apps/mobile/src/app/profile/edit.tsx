import { useState } from 'react';
import { ScrollView, Text, TouchableOpacity, View } from 'react-native';
import { Redirect, useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import Input from '../../components/common/Input';
import Button from '../../components/common/Button';
import GoogleSignInButton from '../../components/auth/GoogleSignInButton';
import useAuthStore from '../../store/authStore';
import authService from '../../services/authService';
import { errorMessage } from '../../utils/errorMessage';
import { Colors } from '../../theme/colors';

export default function EditProfile() {
  const router = useRouter();
  const { user, updateUser } = useAuthStore();
  const [name, setName] = useState(user?.fullName ?? '');
  const [gender, setGender] = useState(user?.gender ?? '');
  const [birth, setBirth] = useState(user?.dateOfBirth?.slice(0, 10) ?? '');
  const [weight, setWeight] = useState(user?.weightKg?.toString() ?? '');
  const [height, setHeight] = useState(user?.heightCm?.toString() ?? '');
  const [blood, setBlood] = useState(user?.bloodGroup ?? '');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  if (!user) return <Redirect href="/(auth)/login" />;
  const save = async () => {
    setBusy(true); setError('');
    try {
      if (name.trim().length < 2) throw new Error('Enter your full name.');
      if (weight && (!Number.isFinite(Number(weight)) || Number(weight) < 1 || Number(weight) > 500)) throw new Error('Weight must be 1–500 kg.');
      if (height && (!Number.isFinite(Number(height)) || Number(height) < 20 || Number(height) > 300)) throw new Error('Height must be 20–300 cm.');
      if (birth && (!/^\d{4}-\d{2}-\d{2}$/.test(birth) || Number.isNaN(Date.parse(birth)) || new Date(birth) > new Date() || new Date(birth).toISOString().slice(0, 10) !== birth)) throw new Error('Enter a valid past birth date as YYYY-MM-DD.');
      if (blood && !['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'].includes(blood.toUpperCase())) throw new Error('Enter a valid blood group, such as O+.');
      updateUser(await authService.updateProfile({ fullName: name.trim(), gender, dateOfBirth: birth ? `${birth}T00:00:00Z` : undefined, weightKg: weight ? Number(weight) : undefined, heightCm: height ? Number(height) : undefined, bloodGroup: blood ? blood.toUpperCase() : undefined }));
      router.replace('/(tabs)/profile');
    } catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
  };
  return <SafeAreaView style={{ flex: 1, backgroundColor: Colors.bgDark }}><ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={{ padding: 24 }}><View style={{ width: '100%', maxWidth: 540, alignSelf: 'center' }}>
    <TouchableOpacity onPress={() => router.back()}><Text style={{ color: Colors.primary, marginBottom: 24 }}>← Back</Text></TouchableOpacity>
    <Text style={{ color: Colors.textPrimary, fontWeight: '800', fontSize: 27, marginBottom: 8 }}>Your health profile</Text><Text style={{ color: Colors.textSecondary, lineHeight: 22, marginBottom: 24 }}>Add the details you want to keep with your records.</Text>
    <View style={{ padding: 20, backgroundColor: Colors.white, borderRadius: 20, borderWidth: 1, borderColor: Colors.border }}><Input label="Full name" value={name} onChangeText={setName} /><Input label="Date of birth (YYYY-MM-DD)" value={birth} onChangeText={setBirth} placeholder="1995-06-15" /><Input label="Gender (optional)" value={gender} onChangeText={setGender} /><Input label="Weight (kg)" value={weight} onChangeText={setWeight} keyboardType="decimal-pad" /><Input label="Height (cm)" value={height} onChangeText={setHeight} keyboardType="decimal-pad" /><Input label="Blood group" value={blood} onChangeText={setBlood} autoCapitalize="characters" placeholder="O+" />{!!error && <Text accessibilityRole="alert" style={{ color: Colors.danger, marginBottom: 16 }}>{error}</Text>}<Button fullWidth title="Save profile" loading={busy} onPress={save} /></View>
    <Text style={{ color: Colors.textPrimary, fontWeight: '700', marginTop: 28, marginBottom: 12 }}>Account access</Text><GoogleSignInButton link />
  </View></ScrollView></SafeAreaView>;
}
