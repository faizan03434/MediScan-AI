import api, { saveTokens, clearTokens } from './api';
import type { ApiResponse, User } from '../types';

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  fullName: string;
  email: string;
  password: string;
  confirmPassword: string;
  gender?: string;
  dateOfBirth?: string;
  weightKg?: number;
  heightCm?: number;
  bloodGroup?: string;
}

export interface AuthResponse {
  accessToken: string;
  refreshToken: string;
  expiresAt: string;
  user: User;
}

export interface OtpChallenge { challengeId: string; expiresAt: string; resendAfterSeconds: number; message: string }
export interface VerifyEmailPayload { email: string; challengeId: string; code: string }

export interface UpdateProfilePayload {
  fullName?: string;
  gender?: string;
  dateOfBirth?: string;
  weightKg?: number;
  heightCm?: number;
  bloodGroup?: string;
  medicalHistory?: string;
}

const authService = {
  async login(payload: LoginPayload): Promise<AuthResponse> {
    const { data } = await api.post<ApiResponse<AuthResponse>>('/auth/login', payload);
    if (!data.success || !data.data) throw new Error(data.message);
    await saveTokens(data.data.accessToken, data.data.refreshToken);
    return data.data;
  },

  async requestRegistration(payload: RegisterPayload): Promise<OtpChallenge> {
    const { data } = await api.post<ApiResponse<OtpChallenge>>('/auth/register/request', payload);
    if (!data.success || !data.data) throw new Error(data.message);
    return data.data;
  },

  async verifyRegistration(payload: VerifyEmailPayload): Promise<AuthResponse> {
    const { data } = await api.post<ApiResponse<AuthResponse>>('/auth/register/verify', payload);
    if (!data.success || !data.data) throw new Error(data.message);
    await saveTokens(data.data.accessToken, data.data.refreshToken);
    return data.data;
  },

  async requestPasswordReset(email: string): Promise<OtpChallenge> {
    const { data } = await api.post<ApiResponse<OtpChallenge>>('/auth/password/forgot', { email });
    if (!data.success || !data.data) throw new Error(data.message);
    return data.data;
  },
  async resetPassword(payload: VerifyEmailPayload & { password: string; confirmPassword: string }): Promise<void> {
    await api.post('/auth/password/reset', payload);
  },
  async googleSignIn(idToken: string, link = false): Promise<AuthResponse | null> {
    const { data } = await api.post<ApiResponse<AuthResponse>>(link ? '/auth/google/link' : '/auth/google', { idToken });
    if (!data.success) throw new Error(data.message);
    if (link) return null;
    if (!data.data) throw new Error('Google sign-in returned no account.');
    await saveTokens(data.data.accessToken, data.data.refreshToken);
    return data.data;
  },

  async logout(refreshToken: string): Promise<void> {
    try {
      await api.post('/auth/revoke', { refreshToken });
    } finally {
      await clearTokens();
    }
  },

  async getProfile(): Promise<User> {
    const { data } = await api.get<ApiResponse<User>>('/auth/profile');
    if (!data.success || !data.data) throw new Error(data.message);
    return data.data;
  },

  async updateProfile(payload: UpdateProfilePayload): Promise<User> {
    const { data } = await api.put<ApiResponse<User>>('/auth/profile', payload);
    if (!data.success || !data.data) throw new Error(data.message);
    return data.data;
  },
};

export default authService;
