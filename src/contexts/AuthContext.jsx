import { createContext, useContext, useEffect, useState } from 'react';
import apiClient from '@/api/client';

const AuthContext = createContext(undefined);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchCurrentUser = async () => {
    const token = localStorage.getItem('auth_token');
    if (!token) {
      setUser(null);
      return null;
    }

    try {
      const { data } = await apiClient.get('/auth/me');
      const normalizedUser = data?.user || data || null;
      setUser(normalizedUser);
      return normalizedUser;
    } catch (error) {
      localStorage.removeItem('auth_token');
      setUser(null);
      throw error;
    }
  };

  useEffect(() => {
    let active = true;
    (async () => {
      setIsLoading(true);
      try {
        await fetchCurrentUser();
      } finally {
        if (active) {
          setIsLoading(false);
        }
      }
    })();

    return () => {
      active = false;
    };
  }, []);

  const refreshUser = async () => {
    try {
      return await fetchCurrentUser();
    } catch {
      return null;
    }
  };

  const login = async (username, password) => {
    const { data } = await apiClient.post('/auth/login', { username, password });
    const token = data.access_token || data.token;
    if (token) {
      localStorage.setItem('auth_token', token);
    }
    const normalizedUser = data?.user || data || null;
    setUser(normalizedUser);
    return normalizedUser;
  };

  const register = async (name, email, password) => {
    const { data } = await apiClient.post('/auth/register', { name, email, password });
    const token = data.access_token || data.token;
    if (token) {
      localStorage.setItem('auth_token', token);
    }
    const normalizedUser = data?.user || data || null;
    setUser(normalizedUser);
    return normalizedUser;
  };

  const logout = () => {
    localStorage.removeItem('auth_token');
    setUser(null);
    window.location.href = '/login';
  };

  const value = {
    user,
    login,
    register,
    logout,
    refreshUser,
    isAuthenticated: !!user,
    isLoading,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth deve ser usado dentro de AuthProvider');
  }
  return context;
}
