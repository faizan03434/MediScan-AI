import React from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  Alert,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useForm, Controller } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { LinearGradient } from 'expo-linear-gradient';
import { SafeAreaView } from 'react-native-safe-area-context';
import useAuthStore from '../../store/authStore';
import Input from '../../components/common/Input';
import Button from '../../components/common/Button';
import { Colors } from '../../theme/colors';

const loginSchema = z.object({
  email:    z.string().email('Enter a valid email'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
});
type LoginForm = z.infer<typeof loginSchema>;

export default function LoginScreen() {
  const router = useRouter();
  const { login, isLoading } = useAuthStore();

  const { control, handleSubmit, formState: { errors } } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginForm) => {
    try {
      await login(data);
      router.replace('/(tabs)/home');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Login failed. Please try again.';
      Alert.alert('Login Failed', msg);
    }
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: Colors.bgDark }}>
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        <ScrollView
          contentContainerStyle={{ flexGrow: 1, paddingHorizontal: 24 }}
          keyboardShouldPersistTaps="handled"
        >
          {/* Header */}
          <View style={{ alignItems: 'center', paddingTop: 60, paddingBottom: 40 }}>
            <View style={{
              width: 72, height: 72, borderRadius: 36,
              backgroundColor: `${Colors.primary}20`,
              alignItems: 'center', justifyContent: 'center',
              marginBottom: 16, borderWidth: 2, borderColor: `${Colors.primary}60`,
            }}>
              <Text style={{ fontSize: 32 }}>🏥</Text>
            </View>
            <Text style={{ color: Colors.textPrimary, fontSize: 28, fontWeight: '800' }}>
              MediScan AI
            </Text>
            <Text style={{ color: Colors.textSecondary, fontSize: 15, marginTop: 6 }}>
              Your personal health scanner
            </Text>
          </View>

          {/* Form */}
          <View style={{
            backgroundColor: Colors.bgCard,
            borderRadius: 24,
            padding: 24,
            borderWidth: 1,
            borderColor: Colors.border,
          }}>
            <Text style={{ color: Colors.textPrimary, fontSize: 22, fontWeight: '700', marginBottom: 24 }}>
              Welcome Back
            </Text>

            <Controller
              control={control}
              name="email"
              render={({ field: { onChange, value } }) => (
                <Input
                  label="Email Address"
                  placeholder="doctor@example.com"
                  keyboardType="email-address"
                  autoCapitalize="none"
                  autoComplete="email"
                  onChangeText={onChange}
                  value={value}
                  error={errors.email?.message}
                />
              )}
            />

            <Controller
              control={control}
              name="password"
              render={({ field: { onChange, value } }) => (
                <Input
                  label="Password"
                  placeholder="Enter your password"
                  isPassword
                  onChangeText={onChange}
                  value={value}
                  error={errors.password?.message}
                />
              )}
            />

            <Button
              title="Sign In"
              loading={isLoading}
              onPress={handleSubmit(onSubmit)}
              fullWidth
              style={{ marginTop: 8 }}
            />
          </View>

          {/* Register link */}
          <View style={{ flexDirection: 'row', justifyContent: 'center', marginTop: 24 }}>
            <Text style={{ color: Colors.textSecondary }}>Don't have an account? </Text>
            <TouchableOpacity onPress={() => router.push('/(auth)/register')}>
              <Text style={{ color: Colors.primary, fontWeight: '700' }}>Create Account</Text>
            </TouchableOpacity>
          </View>

          {/* HIPAA disclaimer */}
          <Text style={{
            color: Colors.textMuted, fontSize: 11, textAlign: 'center',
            marginTop: 24, marginBottom: 16, lineHeight: 16,
          }}>
            🔒 Your health data is encrypted and HIPAA-compliant.{'\n'}
            MediScan AI is a screening tool, not a medical diagnosis.
          </Text>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
