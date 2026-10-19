/**
 * MediScan AI — Axios API Client
 * All HTTP calls to the .NET backend go through this service.
 */
import axios, { create, AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';
import * as SecureStore from '../utils/secureStorage';
import Constants from 'expo-constants';
import { Platform } from 'react-native';
import { notifySessionCleared } from './sessionEvents';

const host = Platform.OS === 'web' && typeof location !== 'undefined'
  ? location.hostname : Constants.expoConfig?.hostUri?.split(':')[0] ?? 'localhost';
export const BASE_URL = process.env.EXPO_PUBLIC_API_URL ?? `http://${host}:5000/api/v1`;
export const resolveImageUrl = (url?: string) => url?.startsWith('/')
  ? `${BASE_URL.replace(/\/api\/v1\/?$/, '')}${url}` : url;

const TOKEN_KEY   = 'mediscan_access_token';
const REFRESH_KEY = 'mediscan_refresh_token';
let sessionRevision = 0;
let tokenWrites: Promise<void> = Promise.resolve();
const writeTokens = (operation: () => Promise<void>) => {
  const next = tokenWrites.then(operation);
  tokenWrites = next.catch(() => {});
  return next;
};

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
  } else { delete config.headers.Authorization; }
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
      originalRequest._retry = true;
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return api(originalRequest);
        });
      }

      isRefreshing = true;
      const revision = sessionRevision;

      try {
        const refreshToken = await SecureStore.getItemAsync(REFRESH_KEY);
        if (!refreshToken) throw new Error('No refresh token');

        const { data } = await axios.post(`${BASE_URL}/auth/refresh`, { refreshToken }, { timeout: 15_000 });
        const newToken = data.data.accessToken;
        const rotated = data.data.refreshToken;
        if (typeof newToken !== 'string' || !newToken || typeof rotated !== 'string' || !rotated) {
          throw new Error('Invalid refresh response');
        }
        await writeTokens(async () => {
          if (sessionRevision !== revision) throw new Error('Session changed during refresh');
          await SecureStore.setItemAsync(TOKEN_KEY, newToken);
          await SecureStore.setItemAsync(REFRESH_KEY, rotated);
        });
        if (sessionRevision !== revision) throw new Error('Session changed during refresh');
        processQueue(null, newToken);
        return api(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        // An obsolete refresh must never clear a newly signed-in account.
        if (sessionRevision === revision) await clearTokens();
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
  const revision = ++sessionRevision;
  notifySessionCleared();
  await writeTokens(async () => {
    if (revision !== sessionRevision) return;
    await SecureStore.setItemAsync(TOKEN_KEY, accessToken);
    await SecureStore.setItemAsync(REFRESH_KEY, refreshToken);
  });
};

export const clearTokens = async () => {
  ++sessionRevision;
  delete api.defaults.headers.common.Authorization;
  notifySessionCleared();
  await writeTokens(async () => {
    await SecureStore.deleteItemAsync(TOKEN_KEY);
    await SecureStore.deleteItemAsync(REFRESH_KEY);
  });
};

export const getAccessToken = () => SecureStore.getItemAsync(TOKEN_KEY);
export const getRefreshToken = () => SecureStore.getItemAsync(REFRESH_KEY);

export default api;
