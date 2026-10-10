import { Tabs, Redirect } from 'expo-router';
import { ActivityIndicator, View } from 'react-native';
import { Feather } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import AppHeader from '../../components/common/AppHeader';
import useAuthStore from '../../store/authStore';
import { Colors } from '../../theme/colors';

export default function TabsLayout() {
  const { isAuthenticated, isLoading } = useAuthStore();
  const insets = useSafeAreaInsets();
  if (isLoading) return <View style={{ flex: 1, backgroundColor: Colors.bgDark, alignItems: 'center', justifyContent: 'center' }}><ActivityIndicator color={Colors.primary} /></View>;
  if (!isAuthenticated) return <Redirect href="/(auth)/login" />;
  return <Tabs screenOptions={{ header: () => <AppHeader />, headerShown: true, tabBarActiveTintColor: Colors.primary, tabBarInactiveTintColor: Colors.textMuted, tabBarStyle: { backgroundColor: Colors.white, borderTopColor: Colors.border, height: 68 + insets.bottom, paddingTop: 8, paddingBottom: 8 + insets.bottom }, tabBarLabelStyle: { fontSize: 11, fontWeight: '600' } }}>
    {([['home', 'Home', 'grid'], ['scan', 'Scan', 'camera'], ['history', 'History', 'clock'], ['medication', 'Medicines', 'package'], ['profile', 'Profile', 'user']] as const).map(([name, title, icon]) => <Tabs.Screen key={name} name={name} options={{ title, tabBarIcon: ({ focused, color }) => <View style={{ width: 52, height: 28, borderRadius: 10, alignItems: 'center', justifyContent: 'center', backgroundColor: focused ? '#EAF4F0' : 'transparent' }}><Feather name={icon} color={color} size={20} /></View> }} />)}
  </Tabs>;
}
