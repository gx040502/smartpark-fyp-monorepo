'use server';

import { serverFetch } from './api';

export async function getCars(queryParams: {
  search?: string,
  status?: string,
  color?: string,
  model?: string,
  date_from?: string,
  date_to?: string,
  date_field?: string,
  page?: string
}) {
  try {
    let queryUrl = `/parking-sessions?page=${queryParams.page || 1}`;
    if (queryParams.search) queryUrl += `&search=${queryParams.search}`;
    if (queryParams.status && queryParams.status !== 'all') queryUrl += `&status=${queryParams.status}`;
    if (queryParams.color && queryParams.color !== 'all') queryUrl += `&color=${queryParams.color}`;
    if (queryParams.model && queryParams.model !== 'all') queryUrl += `&model=${queryParams.model}`;
    if (queryParams.date_from) queryUrl += `&date_from=${queryParams.date_from}`;
    if (queryParams.date_to) queryUrl += `&date_to=${queryParams.date_to}`;
    if (queryParams.date_field && queryParams.date_field !== 'entry_time') queryUrl += `&date_field=${queryParams.date_field}`;

    const res = await serverFetch(queryUrl);
    if (!res.ok) return null;
    
    return await res.json();
  } catch (error) {
    console.error("Error fetching cars:", error);
    return null;
  }
}

export type CarListPaginationParams = NonNullable<Awaited<ReturnType<typeof getCars>>>;

export async function getCarFilterOptions(): Promise<{ colors: string[], models: string[] } | null> {
  try {
    const res = await serverFetch('/parking-sessions/filter-options');
    if (!res.ok) return null;

    return await res.json();
  } catch (error) {
    console.error("Error fetching filter options:", error);
    return null;
  }
}

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
