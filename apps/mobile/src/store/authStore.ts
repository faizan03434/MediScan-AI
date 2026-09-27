import { create } from 'zustand';
import type { User, AuthState } from '../types';
import authService, { LoginPayload, RegisterPayload } from '../services/authService';
import { clearTokens, getAccessToken } from '../services/api';

interface AuthActions {
  login: (payload: LoginPayload) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => Promise<void>;
  loadUser: () => Promise<void>;
  updateUser: (user: User) => void;
  setLoading: (loading: boolean) => void;
}

const useAuthStore = create<AuthState & AuthActions>((set, get) => ({
  // ── State ──────────────────────────────────────────────────
  user: null,
  accessToken: null,
  refreshToken: null,
  isAuthenticated: false,
  isLoading: true,

  // ── Actions ────────────────────────────────────────────────
  login: async (payload) => {
    set({ isLoading: true });
    const response = await authService.login(payload);
    set({
      user: response.user,
      accessToken: response.accessToken,
      refreshToken: response.refreshToken,
      isAuthenticated: true,
      isLoading: false,
    });
  },

  register: async (payload) => {
    set({ isLoading: true });
    const response = await authService.register(payload);
    set({
      user: response.user,
      accessToken: response.accessToken,
      refreshToken: response.refreshToken,
      isAuthenticated: true,
      isLoading: false,
    });
  },

  logout: async () => {
    const { refreshToken } = get();
    set({ isLoading: true });
    if (refreshToken) {
      await authService.logout(refreshToken).catch(() => {});
    }
    await clearTokens();
    set({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
    });
  },

  loadUser: async () => {
    set({ isLoading: true });
    try {
      const token = await getAccessToken();
      if (!token) {
        set({ isAuthenticated: false, isLoading: false });
        return;
      }
      const user = await authService.getProfile();
      set({ user, accessToken: token, isAuthenticated: true, isLoading: false });
    } catch {
      await clearTokens();
      set({ user: null, isAuthenticated: false, isLoading: false });
    }
  },

  updateUser: (user) => set({ user }),
  setLoading: (isLoading) => set({ isLoading }),
}));

export default useAuthStore;
