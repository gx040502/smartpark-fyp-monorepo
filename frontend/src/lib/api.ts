export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api';

/**
 * Basic wrapper around fetch that attaches the Bearer token.
 */
export async function apiFetch(endpoint: string, options: RequestInit = {}) {
  // Try to get token from localStorage (client-side only)
  let token = null;
  if (typeof window !== 'undefined') {
    token = localStorage.getItem('auth_token');
  }

  const headers: Record<string, string> = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    ...((options.headers as Record<string, string>) || {}),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers,
  });

  // Automatically redirect to login if the user is unauthorized (missing or invalid token)
  if (response.status === 401 && typeof window !== 'undefined') {
    localStorage.removeItem('auth_token');
    window.location.href = '/login';
  }

  return response;
}
