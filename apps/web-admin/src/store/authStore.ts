import { create } from 'zustand';
import adminService from '../services/adminService';
import { saveToken, clearToken, getToken } from '../services/api';
import type { AdminUser } from '../types';

interface AuthState {
  user: AdminUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  checkAuth: () => void;
}

const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: !!getToken(),
  isLoading: false,

  login: async (email, password) => {
    set({ isLoading: true });
    const result = await adminService.login(email, password);
    saveToken(result.accessToken);
    set({ user: result.user, isAuthenticated: true, isLoading: false });
  },

  logout: () => {
    clearToken();
    set({ user: null, isAuthenticated: false });
  },

  checkAuth: () => {
    const token = getToken();
    set({ isAuthenticated: !!token });
  },
}));

export default useAuthStore;
