/**
 * MediScan AI — Axios API Client
 * All HTTP calls to the .NET backend go through this service.
 */
import axios, { create, AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';
import * as SecureStore from '../utils/secureStorage';
import Constants from 'expo-constants';
import { Platform } from 'react-native';

const host = Platform.OS === 'web' && typeof location !== 'undefined'
  ? location.hostname : Constants.expoConfig?.hostUri?.split(':')[0] ?? 'localhost';
export const BASE_URL = process.env.EXPO_PUBLIC_API_URL ?? `http://${host}:5000/api/v1`;
export const resolveImageUrl = (url?: string) => url?.startsWith('/')
  ? `${BASE_URL.replace(/\/api\/v1\/?$/, '')}${url}` : url;

const TOKEN_KEY   = 'mediscan_access_token';
const REFRESH_KEY = 'mediscan_refresh_token';

// ── Create Axios instance ──────────────────────────────────────
const api: AxiosInstance = create({
  baseURL: BASE_URL,
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
});

// ── Request interceptor: attach JWT ───────────────────────────
api.interceptors.request.use(async (config: InternalAxiosRequestConfig) => {
  const token = await SecureStore.getItemAsync(TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── Response interceptor: handle 401 → refresh token ─────────
let isRefreshing = false;
let failedQueue: { resolve: (v: string) => void; reject: (e: unknown) => void }[] = [];

const processQueue = (error: unknown, token: string | null) => {
  failedQueue.forEach(({ resolve, reject }) =>
    error ? reject(error) : resolve(token!)
  );
  failedQueue = [];
};

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    if (error.response?.status === 401 && originalRequest && !originalRequest._retry
        && (!originalRequest.url?.startsWith('/auth/') || originalRequest.url === '/auth/profile')) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return api(originalRequest);
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const refreshToken = await SecureStore.getItemAsync(REFRESH_KEY);
        if (!refreshToken) throw new Error('No refresh token');

        const { data } = await axios.post(`${BASE_URL}/auth/refresh`, { refreshToken });
        const newToken = data.data.accessToken;

        await SecureStore.setItemAsync(TOKEN_KEY, newToken);
        await SecureStore.setItemAsync(REFRESH_KEY, data.data.refreshToken);

        api.defaults.headers.common.Authorization = `Bearer ${newToken}`;
        processQueue(null, newToken);
        return api(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        // Clear tokens — force logout
        await SecureStore.deleteItemAsync(TOKEN_KEY);
        await SecureStore.deleteItemAsync(REFRESH_KEY);
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

// ── Token helpers ─────────────────────────────────────────────
export const saveTokens = async (accessToken: string, refreshToken: string) => {
  await SecureStore.setItemAsync(TOKEN_KEY, accessToken);
  await SecureStore.setItemAsync(REFRESH_KEY, refreshToken);
};

export const clearTokens = async () => {
  delete api.defaults.headers.common.Authorization;
  await SecureStore.deleteItemAsync(TOKEN_KEY);
  await SecureStore.deleteItemAsync(REFRESH_KEY);
};

export const getAccessToken = () => SecureStore.getItemAsync(TOKEN_KEY);
export const getRefreshToken = () => SecureStore.getItemAsync(REFRESH_KEY);

export default api;
