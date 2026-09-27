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

  async register(payload: RegisterPayload): Promise<AuthResponse> {
    const { data } = await api.post<ApiResponse<AuthResponse>>('/auth/register', payload);
    if (!data.success || !data.data) throw new Error(data.message);
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
