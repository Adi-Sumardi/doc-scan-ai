import React, { createContext, useContext, useState, useEffect, ReactNode, useRef } from 'react';
import api from '../services/api';

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
  login: (username: string, password: string) => Promise<void>;
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

  // Reset inactivity timer
  const resetInactivityTimer = () => {
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
  };

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
  }, [token]);

  // Load token from localStorage on mount
  useEffect(() => {
    const storedToken = localStorage.getItem('access_token');
    if (storedToken) {
      // Set token first (synchronously in effect)
      setToken(storedToken);
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
      
      // Token might be invalid, clear everything
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
      
      const { access_token } = response.data;
      
      // Set token to localStorage first
      localStorage.setItem('access_token', access_token);
      
      // Then set to state
      setToken(access_token);
      
      // Fetch user info with the new token
      await fetchUserInfo(access_token);
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

  const logout = () => {
    // Clear inactivity timer
    if (inactivityTimerRef.current) {
      clearTimeout(inactivityTimerRef.current);
      inactivityTimerRef.current = null;
    }
    
    setUser(null);
    setToken(null);
    localStorage.removeItem('access_token');
    
    console.log('🚪 User logged out');
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
