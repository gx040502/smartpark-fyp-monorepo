'use server';

import { getAuthToken, removeAuthCookie } from './auth';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api';

/**
 * A server-side equivalent of apiFetch that safely reads the API token from cookies
 * and proxies the request to the backend.
 */
export async function serverFetch(endpoint: string, options: RequestInit = {}) {
  const token = await getAuthToken();

  const headers = new Headers(options.headers);
  headers.set('Accept', 'application/json');
  headers.set('Content-Type', 'application/json');

  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
    cache: 'no-store'
  });

  if (response.status === 401) {
    // If token expired/invalid on server side, wipe it out
    await removeAuthCookie();
  }

  return response;
}
