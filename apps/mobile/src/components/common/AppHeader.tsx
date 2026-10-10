import { Text, TouchableOpacity, View } from 'react-native';
import { Feather } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import useAuthStore from '../../store/authStore';
import { Colors } from '../../theme/colors';

export default function AppHeader() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const user = useAuthStore(s => s.user);
  return <View style={{ backgroundColor: Colors.white, paddingTop: insets.top, borderBottomWidth: 1, borderColor: Colors.border }}>
    <View style={{ height: 68, paddingHorizontal: 20, flexDirection: 'row', alignItems: 'center', gap: 12, width: '100%', maxWidth: 1000, alignSelf: 'center' }}>
      <TouchableOpacity accessibilityLabel="MediScan home" onPress={() => router.navigate('/(tabs)/home')} style={{ flexDirection: 'row', alignItems: 'center', gap: 10, flex: 1 }}>
        <View style={{ backgroundColor: '#EAF4F0', borderRadius: 12, width: 38, height: 38, alignItems: 'center', justifyContent: 'center' }}><Feather name="activity" color={Colors.primary} size={22} /></View>
        <View><Text style={{ fontSize: 18, fontWeight: '800', color: Colors.textPrimary }}>MediScan <Text style={{ color: Colors.primary }}>AI</Text></Text><Text style={{ color: Colors.textMuted, fontSize: 9, letterSpacing: 1.5, marginTop: 2 }}>YOUR HEALTH JOURNAL</Text></View>
      </TouchableOpacity>
      <TouchableOpacity accessibilityLabel="Open your profile" onPress={() => router.navigate('/(tabs)/profile')} style={{ backgroundColor: Colors.bgDark, borderWidth: 1, borderColor: Colors.border, width: 38, height: 38, borderRadius: 19, alignItems: 'center', justifyContent: 'center' }}><Text style={{ color: Colors.primary, fontWeight: '700' }}>{user?.fullName?.charAt(0).toUpperCase() ?? 'M'}</Text></TouchableOpacity>
    </View>
  </View>;
}
