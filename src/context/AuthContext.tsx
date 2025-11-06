import React, { createContext, useContext, useState, useEffect, ReactNode, useRef, useCallback } from 'react';
import api from '../services/api';
import toast from 'react-hot-toast';
import { tokenManager } from '../utils/tokenManager';

interface User {
  id: string;
  username: string;
  email: string;
  full_name?: string;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (username: string, password: string) => Promise<string | undefined>;
  register: (username: string, email: string, password: string, full_name?: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const fetchingUserRef = useRef(false); // Prevent duplicate calls
  const inactivityTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Inactivity timeout: 30 minutes
  const INACTIVITY_TIMEOUT = 30 * 60 * 1000; // 30 minutes in milliseconds

  // Memoize logout to prevent dependency issues
  const logout = useCallback(() => {
    // Clear inactivity timer
    if (inactivityTimerRef.current) {
      clearTimeout(inactivityTimerRef.current);
      inactivityTimerRef.current = null;
    }

    setUser(null);
    setToken(null);

    // Clear all auth-related data including tokens
    tokenManager.clearTokens();
    localStorage.removeItem('user');
    sessionStorage.clear();

    console.log('🚪 User logged out');
  }, []);

  // Reset inactivity timer with stable logout reference
  const resetInactivityTimer = useCallback(() => {
    // Clear existing timer
    if (inactivityTimerRef.current) {
      clearTimeout(inactivityTimerRef.current);
    }

    // Set new timer - auto logout after 30 min of inactivity
    if (token) {
      inactivityTimerRef.current = setTimeout(() => {
        console.warn('⏰ Session expired due to inactivity');
        logout();
      }, INACTIVITY_TIMEOUT);
    }
  }, [token, logout, INACTIVITY_TIMEOUT]);

  // Track user activity
  useEffect(() => {
    if (!token) return;

    // Events that indicate user activity
    const activityEvents = ['mousedown', 'keydown', 'scroll', 'touchstart', 'click'];

    const handleActivity = () => {
      resetInactivityTimer();
    };

    // Add event listeners
    activityEvents.forEach(event => {
      window.addEventListener(event, handleActivity);
    });

    // Initial timer setup
    resetInactivityTimer();

    // Cleanup
    return () => {
      activityEvents.forEach(event => {
        window.removeEventListener(event, handleActivity);
      });
      if (inactivityTimerRef.current) {
        clearTimeout(inactivityTimerRef.current);
      }
    };
  }, [token, resetInactivityTimer]);

  // Load token from localStorage on mount
  useEffect(() => {
    // Check both 'token' and 'access_token' for backward compatibility
    const storedToken = tokenManager.getAccessToken() || localStorage.getItem('access_token');
    if (storedToken) {
      // Set token first (synchronously in effect)
      setToken(storedToken);
      // Initialize token manager for auto-refresh
      tokenManager.initialize();
      // Then fetch user info
      fetchUserInfo(storedToken);
    } else {
      setIsLoading(false);
    }
  }, []);

  const fetchUserInfo = async (authToken: string) => {
    // Prevent duplicate calls
    if (fetchingUserRef.current) {
      return;
    }

    fetchingUserRef.current = true;
    
    try {
      // Use api instance which already has interceptor for token
      // But we pass token explicitly here for initial load
      const response = await api.get('/api/me', {
        headers: {
          Authorization: `Bearer ${authToken}`
        }
      });
      setUser(response.data);
    } catch (error: any) {
      console.error('Failed to fetch user info:', error);
      
      // Provide more descriptive error messages based on error type
      let errorMessage = 'Failed to fetch user information. Please try again.';
      
      if (error.response) {
        // Server responded with error
        if (error.response.status === 401) {
          errorMessage = 'Session expired. Please login again.';
        } else if (error.response.status === 403) {
          errorMessage = 'Access denied. Please check your permissions.';
        } else if (error.response.status >= 500) {
          errorMessage = 'Server error. Please try again later.';
        } else if (error.response.data?.detail) {
          errorMessage = error.response.data.detail;
        }
      } else if (error.request) {
        // Network error - no response received
        errorMessage = 'Network error. Please check your internet connection.';
      }
      
      toast.error(errorMessage);

      // Token might be invalid, clear everything
      localStorage.removeItem('token');
      localStorage.removeItem('access_token');
      setToken(null);
      setUser(null);

      // If it's a 401, user will be redirected by axios interceptor
    } finally {
      setIsLoading(false);
      fetchingUserRef.current = false;
    }
  };

  const login = async (username: string, password: string) => {
    try {
      // Use api instance for consistent baseURL
      const response = await api.post('/api/login', {
        username,
        password
      });

      const { access_token, refresh_token, expires_in } = response.data;

      // Store tokens using tokenManager for auto-refresh
      tokenManager.setTokens({
        access_token,
        refresh_token,
        expires_in,
        token_type: 'bearer'
      });

      // Then set to state
      setToken(access_token);

      // Fetch user info with the new token
      await fetchUserInfo(access_token);

      console.log('✅ Login successful - Token will auto-refresh in', Math.floor(expires_in / 60), 'minutes');

      // Check if there's a redirect path saved
      const redirectPath = localStorage.getItem('redirectAfterLogin');
      if (redirectPath) {
        localStorage.removeItem('redirectAfterLogin');
        // Will be handled by the component that uses this
        return redirectPath;
      }
    } catch (error: any) {
      console.error('Login failed:', error);

      // Extract detailed error message
      const errorMessage = error.response?.data?.detail
        || error.response?.data?.message
        || error.message
        || 'Login failed. Please check your credentials.';

      throw new Error(errorMessage);
    }
  };

  const register = async (username: string, email: string, password: string, full_name?: string) => {
    try {
      // Use api instance for consistent baseURL
      await api.post('/api/register', {
        username,
        email,
        password,
        full_name
      });

      // Auto-login after registration
      await login(username, password);
    } catch (error: any) {
      console.error('Registration failed:', error);

      // Extract detailed error message
      const errorMessage = error.response?.data?.detail
        || error.response?.data?.message
        || error.message
        || 'Registration failed. Please try again.';

      throw new Error(errorMessage);
    }
  };

  const value: AuthContextType = {
    user,
    token,
    login,
    register,
    logout,
    isAuthenticated: !!token && !!user,
    isLoading
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
