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
  const authenticated = useAuthStore((s) => s.isAuthenticated);
  useEffect(() => {
    const unsubscribe = useAuthStore.subscribe((state, previous) => {
      if (state.user?.id !== previous.user?.id) queryClient.clear();
    });
    loadUser();
    return unsubscribe;
  }, [loadUser]);

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <QueryClientProvider client={queryClient}>
        <StatusBar style="dark" backgroundColor={Colors.bgDark} />
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
          <Stack.Screen name="index" options={{ animation: 'none' }} />
          <Stack.Screen name="information/[topic]" />
          <Stack.Screen name="deletion-status" />
          {/* Native protected routes remove private modals and their history on session expiry. */}
          <Stack.Protected guard={authenticated}>
          <Stack.Screen name="(tabs)" options={{ animation: 'none' }} />

          {/* Scan modal */}
          <Stack.Screen name="scan/[type]" options={{ animation: 'slide_from_bottom', presentation: 'modal' }} />

          {/* Comparison screen */}
          <Stack.Screen name="compare/[scanId]" options={{ animation: 'slide_from_right' }} />

          {/* Doctor portal */}
          <Stack.Screen name="doctor/index" options={{ animation: 'slide_from_right' }} />
          <Stack.Screen name="doctor/request-access" options={{ animation: 'slide_from_right' }} />
          <Stack.Screen name="doctor/consents" options={{ animation: 'slide_from_right' }} />
          <Stack.Screen name="doctor/patient/[id]" options={{ animation: 'slide_from_right' }} />
          <Stack.Screen name="doctor/patient/scan/[scanId]" />
          <Stack.Screen name="record/[id]" />
          <Stack.Screen name="profile/edit" />
          <Stack.Screen name="profile/data" />
          <Stack.Screen name="profile/delete" />
          <Stack.Screen name="profile/activity" />
          </Stack.Protected>
        </Stack>
        <Toast />
      </QueryClientProvider>
    </GestureHandlerRootView>
  );
}
