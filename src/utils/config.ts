/**
 * Configuration utilities for API base URL determination
 *
 * This module provides a centralized way to determine the API base URL
 * based on the environment (development, production) and configuration.
 */

/**
 * Get the API base URL based on environment and hostname
 *
 * Priority:
 * 1. VITE_API_URL environment variable (if set)
 * 2. Production domain (adilabs.id) -> use relative path
 * 3. Development (localhost/127.0.0.1) -> http://localhost:8000
 * 4. Default -> relative path (production fallback)
 *
 * @returns {string} The API base URL
 */
export const getApiBaseUrl = (): string => {
  // Check environment variable first
  if (import.meta.env.VITE_API_URL) {
    console.log('Using API URL from environment:', import.meta.env.VITE_API_URL);
    return import.meta.env.VITE_API_URL;
  }

  const hostname = window.location.hostname;

  // Production environment
  if (hostname === 'docscan.adilabs.id' || hostname.includes('adilabs.id')) {
    console.log('Production mode: backend already has /api prefix');
    return ''; // use relative path
  }

  // Development environment
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    console.log('Development mode: using localhost:8000');
    return 'http://localhost:8000';
  }

  // Default to production
  console.log('Unknown domain, defaulting to production');
  return '';
};

/**
 * Get the current environment mode
 * @returns {'development' | 'production'} The current environment
 */
export const getEnvironment = (): 'development' | 'production' => {
  const hostname = window.location.hostname;

  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return 'development';
  }

  return 'production';
};

/**
 * Check if running in development mode
 * @returns {boolean} True if in development mode
 */
export const isDevelopment = (): boolean => {
  return getEnvironment() === 'development';
};

/**
 * Check if running in production mode
 * @returns {boolean} True if in production mode
 */
export const isProduction = (): boolean => {
  return getEnvironment() === 'production';
};
