import { useEffect } from 'react';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import Toast from 'react-native-toast-message';
import useAuthStore from '../store/authStore';
import { Colors } from '../theme/colors';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      staleTime: 1000 * 60 * 5, // 5 minutes
    },
  },
});

export default function RootLayout() {
  const loadUser = useAuthStore((s) => s.loadUser);

  useEffect(() => {
    loadUser();
  }, [loadUser]);

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <QueryClientProvider client={queryClient}>
        <StatusBar style="light" backgroundColor={Colors.bgDark} />
        <Stack
          screenOptions={{
            headerShown: false,
            contentStyle: { backgroundColor: Colors.bgDark },
            animation: 'slide_from_right',
          }}
        >
          {/* Onboarding — no gestures, no back */}
          <Stack.Screen name="onboarding" options={{ gestureEnabled: false, animation: 'fade' }} />

          {/* Auth group */}
          <Stack.Screen name="(auth)" options={{ animation: 'fade' }} />

          {/* Main tabs */}
          <Stack.Screen name="(tabs)" options={{ animation: 'none' }} />

          {/* Scan modal */}
          <Stack.Screen name="scan/[type]" options={{ animation: 'slide_from_bottom', presentation: 'modal' }} />

          {/* Comparison screen */}
          <Stack.Screen name="compare/[scanId]" options={{ animation: 'slide_from_right' }} />

          {/* Doctor portal */}
          <Stack.Screen name="doctor" options={{ animation: 'slide_from_right' }} />
          <Stack.Screen name="doctor/request-access" options={{ animation: 'slide_from_right' }} />
          <Stack.Screen name="doctor/consents" options={{ animation: 'slide_from_right' }} />
          <Stack.Screen name="doctor/patient/[id]" options={{ animation: 'slide_from_right' }} />
        </Stack>
        <Toast />
      </QueryClientProvider>
    </GestureHandlerRootView>
  );
}
