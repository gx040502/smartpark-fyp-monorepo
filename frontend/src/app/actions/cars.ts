'use server';

import { serverFetch } from './api';

export async function getCars(queryParams: { search?: string, status?: string, color?: string, page?: string }) {
  try {
    let queryUrl = `/parking-sessions?page=${queryParams.page || 1}`;
    if (queryParams.search) queryUrl += `&search=${queryParams.search}`;
    if (queryParams.status && queryParams.status !== 'all') queryUrl += `&status=${queryParams.status}`;
    if (queryParams.color && queryParams.color !== 'all') queryUrl += `&color=${queryParams.color}`;

    const res = await serverFetch(queryUrl);
    if (!res.ok) return null;
    
    return await res.json();
  } catch (error) {
    console.error("Error fetching cars:", error);
    return null;
  }
}

export type CarListPaginationParams = NonNullable<Awaited<ReturnType<typeof getCars>>>;

export async function getCarDetails(id: number | string) {
  try {
    const res = await serverFetch(`/parking-sessions/${id}`);
    if (!res.ok) return null;
    
    return await res.json();
  } catch (error) {
    console.error(`Error fetching car details for ID ${id}:`, error);
    return null;
  }
}
