import { createContext, useContext, useState, useEffect, useCallback } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8001';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Check for existing session on mount
  useEffect(() => {
    const checkAuth = async () => {
      // Check for guest session first
      const isGuest = localStorage.getItem('guest_session');
      if (isGuest) {
        const guestUser = JSON.parse(localStorage.getItem('guest_user') || '{}');
        if (guestUser.id) {
          setUser(guestUser);
          setLoading(false);
          return;
        }
      }

      const accessToken = localStorage.getItem('access_token');
      if (!accessToken) {
        setLoading(false);
        return;
      }

      try {
        const response = await fetch(`${API_BASE}/api/auth/me`, {
          headers: {
            'Authorization': `Bearer ${accessToken}`,
          },
        });

        if (response.ok) {
          const userData = await response.json();
          setUser(userData);
        } else {
          // Token invalid, clear and require re-login
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
        }
      } catch (err) {
        console.error('Auth check failed:', err);
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
  }, []);

  const setTokens = useCallback((accessToken, refreshTokenValue) => {
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshTokenValue);
  }, []);

  const clearTokens = useCallback(() => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  }, []);

  const register = async (email, password, name) => {
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, name }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Registration failed');
      }

      const data = await response.json();
      setTokens(data.access_token, data.refresh_token);
      setUser(data.user);
      return data;
    } catch (err) {
      setError(err.message);
      throw err;
    }
  };

  const login = async (email, password) => {
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Login failed');
      }

      const data = await response.json();
      setTokens(data.access_token, data.refresh_token);
      setUser(data.user);
      return data;
    } catch (err) {
      setError(err.message);
      throw err;
    }
  };

  const loginWithGoogle = async (credential) => {
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/api/auth/google`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ credential }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Google login failed');
      }

      const data = await response.json();
      setTokens(data.access_token, data.refresh_token);
      setUser(data.user);
      return data;
    } catch (err) {
      setError(err.message);
      throw err;
    }
  };

  const loginAsGuest = async () => {
    setError(null);
    // Create a guest session without backend authentication
    // This allows users to try the app without registering
    const guestUser = {
      id: `guest-${Date.now()}`,
      email: 'guest@llm-council.local',
      name: 'Guest User',
      avatar_url: null,
      is_verified: false,
      is_admin: false,
      is_guest: true,
      created_at: new Date().toISOString(),
    };

    // Store a guest token marker
    localStorage.setItem('guest_session', 'true');
    localStorage.setItem('guest_user', JSON.stringify(guestUser));
    setUser(guestUser);
    return { user: guestUser };
  };

  const refreshToken = async () => {
    const storedRefresh = localStorage.getItem('refresh_token');
    if (!storedRefresh) {
      throw new Error('No refresh token');
    }

    try {
      const response = await fetch(`${API_BASE}/api/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: storedRefresh }),
      });

      if (!response.ok) {
        clearTokens();
        setUser(null);
        throw new Error('Token refresh failed');
      }

      const data = await response.json();
      setTokens(data.access_token, data.refresh_token);
      setUser(data.user);
      return data.access_token;
    } catch (err) {
      clearTokens();
      setUser(null);
      throw err;
    }
  };

  const logout = async () => {
    // Handle guest session logout
    if (localStorage.getItem('guest_session')) {
      localStorage.removeItem('guest_session');
      localStorage.removeItem('guest_user');
      setUser(null);
      return;
    }

    const refreshTokenValue = localStorage.getItem('refresh_token');

    try {
      if (refreshTokenValue) {
        await fetch(`${API_BASE}/api/auth/logout`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshTokenValue }),
        });
      }
    } catch (err) {
      console.error('Logout error:', err);
    } finally {
      clearTokens();
      setUser(null);
    }
  };

  const updateProfile = async (updates) => {
    const accessToken = localStorage.getItem('access_token');
    const params = new URLSearchParams();
    if (updates.name) params.append('name', updates.name);
    if (updates.avatar_url) params.append('avatar_url', updates.avatar_url);

    const response = await fetch(`${API_BASE}/api/auth/me?${params}`, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      },
    });

    if (!response.ok) {
      throw new Error('Failed to update profile');
    }

    const updatedUser = await response.json();
    setUser(updatedUser);
    return updatedUser;
  };

  const getAccessToken = useCallback(() => {
    return localStorage.getItem('access_token');
  }, []);

  const value = {
    user,
    loading,
    error,
    isAuthenticated: !!user,
    isGuest: user?.is_guest || false,
    register,
    login,
    loginWithGoogle,
    loginAsGuest,
    logout,
    refreshToken,
    updateProfile,
    getAccessToken,
    clearError: () => setError(null),
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export default AuthContext;
