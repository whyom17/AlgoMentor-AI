/**
 * Zustand auth store.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { api } from '@/lib/api';
import type { User, TokenResponse } from '@/types/api';

interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, username: string, password: string) => Promise<void>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isLoading: false,

      login: async (email, password) => {
        set({ isLoading: true });
        try {
          const { data } = await api.post<TokenResponse>('/auth/login', { email, password });
          localStorage.setItem('algomentor_token', data.access_token);
          const meRes = await api.get<User>('/auth/me');
          set({ token: data.access_token, user: meRes.data });
        } finally {
          set({ isLoading: false });
        }
      },

      register: async (email, username, password) => {
        set({ isLoading: true });
        try {
          const { data } = await api.post<TokenResponse>('/auth/register', {
            email,
            username,
            password,
          });
          localStorage.setItem('algomentor_token', data.access_token);
          const meRes = await api.get<User>('/auth/me');
          set({ token: data.access_token, user: meRes.data });
        } finally {
          set({ isLoading: false });
        }
      },

      logout: () => {
        localStorage.removeItem('algomentor_token');
        localStorage.removeItem('algomentor_user');
        set({ user: null, token: null });
        window.location.href = '/login';
      },
    }),
    {
      name: 'algomentor_user',
      partialize: (state) => ({ user: state.user, token: state.token }),
    }
  )
);
