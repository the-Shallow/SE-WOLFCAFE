/**
 * API Configuration
 *
 * Centralized configuration for backend API endpoints.
 * Uses environment variables to support different environments (dev, staging, production).
 */

/**
 * Get the backend API base URL from environment variables
 * Falls back to production URL if not set
 */
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://safebites-yu1o.onrender.com';

/**
 * API endpoint paths
 */
export const API_ENDPOINTS = {
  // User endpoints
  users: {
    login: (username: string, password: string) =>
      `${API_BASE_URL}/users/login?username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`,
    signup: `${API_BASE_URL}/users/signup`,
    me: `${API_BASE_URL}/users/me`,
  },
  // Restaurant endpoints
  restaurants: {
    base: `${API_BASE_URL}/restaurants`,
    byId: (id: string) => `${API_BASE_URL}/restaurants/${id}`,
    menu: (id: string) => `${API_BASE_URL}/restaurants/${id}/menu`,
    chat: (id: string) => `${API_BASE_URL}/restaurants/${id}/chat`,
  },
} as const;

/**
 * Helper function to check if API is configured correctly
 */
export const isApiConfigured = (): boolean => {
  return !!API_BASE_URL;
};

/**
 * Log current API configuration (for debugging)
 */
export const logApiConfig = (): void => {
  console.log('[API Config]', {
    baseUrl: API_BASE_URL,
    environment: import.meta.env.MODE,
  });
};
