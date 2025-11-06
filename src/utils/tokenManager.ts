/**
 * Token Manager
 * Handles automatic token refresh before expiration
 */

interface TokenData {
  access_token: string;
  refresh_token: string;
  expires_in: number; // in seconds
  token_type: string;
}

class TokenManager {
  private refreshTimer: NodeJS.Timeout | null = null;
  private isRefreshing = false;

  /**
   * Store tokens in localStorage and schedule auto-refresh
   */
  setTokens(tokenData: TokenData): void {
    localStorage.setItem('token', tokenData.access_token);
    localStorage.setItem('refresh_token', tokenData.refresh_token);
    localStorage.setItem('token_expires_at', String(Date.now() + tokenData.expires_in * 1000));

    // Schedule refresh 5 minutes before expiration
    this.scheduleTokenRefresh(tokenData.expires_in);
  }

  /**
   * Get current access token
   */
  getAccessToken(): string | null {
    return localStorage.getItem('token');
  }

  /**
   * Get refresh token
   */
  getRefreshToken(): string | null {
    return localStorage.getItem('refresh_token');
  }

  /**
   * Check if token is about to expire (within 10 minutes)
   */
  isTokenExpiringSoon(): boolean {
    const expiresAt = localStorage.getItem('token_expires_at');
    if (!expiresAt) return true;

    const expirationTime = parseInt(expiresAt);
    const now = Date.now();
    const tenMinutes = 10 * 60 * 1000;

    return expirationTime - now < tenMinutes;
  }

  /**
   * Schedule automatic token refresh
   */
  private scheduleTokenRefresh(expiresIn: number): void {
    // Clear existing timer
    if (this.refreshTimer) {
      clearTimeout(this.refreshTimer);
    }

    // Refresh 5 minutes before expiration
    const refreshTime = (expiresIn - 5 * 60) * 1000;

    if (refreshTime > 0) {
      this.refreshTimer = setTimeout(() => {
        this.refreshAccessToken();
      }, refreshTime);

      console.log(`🔄 Token refresh scheduled in ${refreshTime / 1000 / 60} minutes`);
    }
  }

  /**
   * Refresh access token using refresh token
   */
  async refreshAccessToken(): Promise<boolean> {
    if (this.isRefreshing) {
      console.log('🔄 Token refresh already in progress');
      return false;
    }

    const refreshToken = this.getRefreshToken();
    if (!refreshToken) {
      console.error('❌ No refresh token available');
      this.clearTokens();
      return false;
    }

    this.isRefreshing = true;

    try {
      console.log('🔄 Refreshing access token...');

      const response = await fetch('/api/refresh', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!response.ok) {
        console.error('❌ Token refresh failed:', response.status);
        this.clearTokens();
        window.location.href = '/login';
        return false;
      }

      const tokenData: TokenData = await response.json();
      this.setTokens(tokenData);

      console.log('✅ Access token refreshed successfully');
      return true;
    } catch (error) {
      console.error('❌ Token refresh error:', error);
      this.clearTokens();
      window.location.href = '/login';
      return false;
    } finally {
      this.isRefreshing = false;
    }
  }

  /**
   * Clear all tokens and cancel refresh timer
   */
  clearTokens(): void {
    localStorage.removeItem('token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('token_expires_at');

    if (this.refreshTimer) {
      clearTimeout(this.refreshTimer);
      this.refreshTimer = null;
    }
  }

  /**
   * Initialize token manager (call on app start if user is logged in)
   */
  initialize(): void {
    const token = this.getAccessToken();
    const refreshToken = this.getRefreshToken();
    const expiresAt = localStorage.getItem('token_expires_at');

    if (token && refreshToken && expiresAt) {
      const expirationTime = parseInt(expiresAt);
      const now = Date.now();
      const remainingTime = Math.max(0, expirationTime - now);

      if (remainingTime > 0) {
        // Schedule refresh based on remaining time
        this.scheduleTokenRefresh(remainingTime / 1000);
        console.log('✅ Token manager initialized');
      } else {
        // Token already expired, refresh immediately
        console.log('⏰ Token expired, refreshing immediately...');
        this.refreshAccessToken();
      }
    }
  }
}

// Export singleton instance
export const tokenManager = new TokenManager();
