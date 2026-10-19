import { create } from 'zustand';
import type { User, AuthState } from '../types';
import authService, { LoginPayload, AuthResponse } from '../services/authService';
import { clearTokens, getAccessToken, getRefreshToken } from '../services/api';
import { onSessionCleared, sessionVersion } from '../services/sessionEvents';

interface AuthActions {
  login: (payload: LoginPayload) => Promise<void>;
  acceptAuth: (response: AuthResponse) => void;
  logout: () => Promise<void>;
  loadUser: () => Promise<void>;
  updateUser: (user: User) => void;
  setLoading: (loading: boolean) => void;
}

const useAuthStore = create<AuthState & AuthActions>((set) => ({
  // ── State ──────────────────────────────────────────────────
  user: null,
  accessToken: null,
  refreshToken: null,
  isAuthenticated: false,
  isLoading: true,

  // ── Actions ────────────────────────────────────────────────
  login: async (payload) => {
    const revision = sessionVersion();
    set({ isLoading: true });
    try {
    const response = await authService.login(payload);
    if (sessionVersion() !== revision + 1) throw new Error('Session changed. Sign in again.');
    set({
      user: response.user,
      accessToken: response.accessToken,
      refreshToken: response.refreshToken,
      isAuthenticated: true,
      isLoading: false,
    });
    } finally { set({ isLoading: false }); }
  },

  acceptAuth: (response) => {
    set({
      user: response.user,
      accessToken: response.accessToken,
      refreshToken: response.refreshToken,
      isAuthenticated: true,
      isLoading: false,
    });
  },

  logout: async () => {
    set({ isLoading: true });
    const refreshToken = await getRefreshToken();
    if (refreshToken) {
      await authService.logout(refreshToken).catch(() => {});
    } else { await clearTokens(); }
  },

  loadUser: async () => {
    const revision = sessionVersion();
    set({ isLoading: true });
    try {
      const token = await getAccessToken();
      if (!token) {
        if (revision === sessionVersion()) await clearTokens();
        return;
      }
      const user = await authService.getProfile();
      const accessToken = await getAccessToken(); const refreshToken = await getRefreshToken();
      if (revision === sessionVersion()) set({ user, accessToken, refreshToken, isAuthenticated: true, isLoading: false });
    } catch {
      if (revision === sessionVersion()) await clearTokens();
    }
  },

  updateUser: (user) => set({ user }),
  setLoading: (isLoading) => set({ isLoading }),
}));

onSessionCleared(() => useAuthStore.setState({
  user: null, accessToken: null, refreshToken: null, isAuthenticated: false, isLoading: false,
}));

export default useAuthStore;
