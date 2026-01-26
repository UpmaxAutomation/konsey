import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { safeFetch, NetworkError } from '../api/client';

import { API_BASE } from '../api/client';

const AuthContext = createContext(null);

// Mutex for preventing concurrent token refresh attempts
let refreshPromise = null;

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Check for existing session on mount
  useEffect(() => {
    const checkAuth = async () => {
      const accessToken = localStorage.getItem('access_token');
      if (!accessToken) {
        setLoading(false);
        return;
      }

      try {
        const response = await fetch(`${API_BASE}/auth/me`, {
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
      // Log API URL for debugging (only in development)
      if (import.meta.env.DEV) {
        console.log('Registering with API:', API_BASE);
      }
      
      const response = await safeFetch(`${API_BASE}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, name }),
      }, 'registration');

      if (!response.ok) {
        let errorMessage = 'Registration failed';
        try {
          const data = await response.json();
          errorMessage = data.detail || errorMessage;
        } catch (e) {
          // If response is not JSON, use status text
          errorMessage = response.statusText || errorMessage;
        }
        throw new Error(errorMessage);
      }

      const data = await response.json();
      setTokens(data.access_token, data.refresh_token);
      setUser(data.user);
      return data;
    } catch (err) {
      // Provide better error messages for network errors
      if (err instanceof NetworkError) {
        const message = err.message || 'Failed to connect to server. Please check your internet connection and ensure the backend server is running.';
        setError(message);
        throw new Error(message);
      }
      setError(err.message || 'Registration failed. Please try again.');
      throw err;
    }
  };

  const login = async (email, password) => {
    setError(null);
    try {
      const response = await safeFetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      }, 'login');

      if (!response.ok) {
        let errorMessage = 'Login failed';
        try {
          const data = await response.json();
          errorMessage = data.detail || errorMessage;
        } catch (e) {
          errorMessage = response.statusText || errorMessage;
        }
        throw new Error(errorMessage);
      }

      const data = await response.json();
      setTokens(data.access_token, data.refresh_token);
      setUser(data.user);
      return data;
    } catch (err) {
      if (err instanceof NetworkError) {
        const message = err.message || 'Failed to connect to server. Please check your internet connection and ensure the backend server is running.';
        setError(message);
        throw new Error(message);
      }
      setError(err.message || 'Login failed. Please try again.');
      throw err;
    }
  };

  const loginWithGoogle = async (credential) => {
    setError(null);
    try {
      const response = await safeFetch(`${API_BASE}/auth/google`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ credential }),
      }, 'google login');

      if (!response.ok) {
        let errorMessage = 'Google login failed';
        try {
          const data = await response.json();
          errorMessage = data.detail || errorMessage;
        } catch (e) {
          errorMessage = response.statusText || errorMessage;
        }
        throw new Error(errorMessage);
      }

      const data = await response.json();
      setTokens(data.access_token, data.refresh_token);
      setUser(data.user);
      return data;
    } catch (err) {
      if (err instanceof NetworkError) {
        const message = err.message || 'Failed to connect to server. Please check your internet connection.';
        setError(message);
        throw new Error(message);
      }
      setError(err.message || 'Google login failed. Please try again.');
      throw err;
    }
  };

  const refreshToken = async () => {
    // If a refresh is already in progress, wait for it instead of starting another
    if (refreshPromise) {
      return refreshPromise;
    }

    const storedRefresh = localStorage.getItem('refresh_token');
    if (!storedRefresh) {
      throw new Error('No refresh token');
    }

    // Create the refresh promise and store it to prevent concurrent refreshes
    refreshPromise = (async () => {
      try {
        const response = await fetch(`${API_BASE}/auth/refresh`, {
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
      } finally {
        // Clear the promise so future refresh attempts can proceed
        refreshPromise = null;
      }
    })();

    return refreshPromise;
  };

  const logout = async () => {
    const refreshTokenValue = localStorage.getItem('refresh_token');

    try {
      if (refreshTokenValue) {
        await fetch(`${API_BASE}/auth/logout`, {
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

    const response = await fetch(`${API_BASE}/auth/me?${params}`, {
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
    register,
    login,
    loginWithGoogle,
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
