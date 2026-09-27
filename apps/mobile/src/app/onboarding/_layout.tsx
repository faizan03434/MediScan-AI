import { Stack } from 'expo-router';
import { Colors } from '../../theme/colors';

export default function OnboardingLayout() {
  return (
    <Stack
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: Colors.bgDark },
        animation: 'slide_from_right',
        gestureEnabled: false, // can't swipe back during onboarding
      }}
    />
  );
}
