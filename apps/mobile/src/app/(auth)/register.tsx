import React from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, Alert, KeyboardAvoidingView, Platform,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useForm, Controller } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { SafeAreaView } from 'react-native-safe-area-context';
import useAuthStore from '../../store/authStore';
import Input from '../../components/common/Input';
import Button from '../../components/common/Button';
import { Colors } from '../../theme/colors';

const registerSchema = z.object({
  fullName:        z.string().min(2, 'Name must be at least 2 characters'),
  email:           z.string().email('Enter a valid email'),
  password:        z.string().min(8, 'Minimum 8 characters, include 1 uppercase and 1 number'),
  confirmPassword: z.string(),
  gender:          z.enum(['Male', 'Female', 'Other']).optional(),
}).refine(d => d.password === d.confirmPassword, {
  message: 'Passwords do not match',
  path: ['confirmPassword'],
});

type RegisterForm = z.infer<typeof registerSchema>;

export default function RegisterScreen() {
  const router = useRouter();
  const { register: registerUser, isLoading } = useAuthStore();

  const { control, handleSubmit, formState: { errors } } = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
  });

  const onSubmit = async (data: RegisterForm) => {
    try {
      await registerUser(data);
      router.replace('/(tabs)/home');
    } catch (err: unknown) {
      Alert.alert('Registration Failed', err instanceof Error ? err.message : 'Please try again.');
    }
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: Colors.bgDark }}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
        <ScrollView contentContainerStyle={{ flexGrow: 1, paddingHorizontal: 24 }} keyboardShouldPersistTaps="handled">
          <TouchableOpacity onPress={() => router.back()} style={{ marginTop: 16, marginBottom: 8 }}>
            <Text style={{ color: Colors.primary }}>← Back</Text>
          </TouchableOpacity>

          <Text style={{ color: Colors.textPrimary, fontSize: 28, fontWeight: '800', marginBottom: 6 }}>
            Create Account
          </Text>
          <Text style={{ color: Colors.textSecondary, marginBottom: 24 }}>
            Start your health monitoring journey
          </Text>

          <View style={{ backgroundColor: Colors.bgCard, borderRadius: 24, padding: 24, borderWidth: 1, borderColor: Colors.border }}>
            <Controller control={control} name="fullName"
              render={({ field: { onChange, value } }) => (
                <Input label="Full Name" placeholder="Ali Hassan" onChangeText={onChange} value={value} error={errors.fullName?.message} />
              )}
            />
            <Controller control={control} name="email"
              render={({ field: { onChange, value } }) => (
                <Input label="Email Address" placeholder="ali@example.com" keyboardType="email-address" autoCapitalize="none" onChangeText={onChange} value={value} error={errors.email?.message} />
              )}
            />
            <Controller control={control} name="password"
              render={({ field: { onChange, value } }) => (
                <Input label="Password" placeholder="Min 8 chars, 1 uppercase, 1 number" isPassword onChangeText={onChange} value={value} error={errors.password?.message} />
              )}
            />
            <Controller control={control} name="confirmPassword"
              render={({ field: { onChange, value } }) => (
                <Input label="Confirm Password" placeholder="Repeat your password" isPassword onChangeText={onChange} value={value} error={errors.confirmPassword?.message} />
              )}
            />

            <Button title="Create Account" loading={isLoading} onPress={handleSubmit(onSubmit)} fullWidth style={{ marginTop: 8 }} />
          </View>

          <View style={{ flexDirection: 'row', justifyContent: 'center', marginTop: 20, marginBottom: 16 }}>
            <Text style={{ color: Colors.textSecondary }}>Already have an account? </Text>
            <TouchableOpacity onPress={() => router.push('/(auth)/login')}>
              <Text style={{ color: Colors.primary, fontWeight: '700' }}>Sign In</Text>
            </TouchableOpacity>
          </View>

          <Text style={{ color: Colors.textMuted, fontSize: 11, textAlign: 'center', lineHeight: 16, marginBottom: 20 }}>
            By creating an account you agree to our Terms of Service and Privacy Policy. Your health data is encrypted and HIPAA-compliant.
          </Text>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
