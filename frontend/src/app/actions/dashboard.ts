'use server';

import { serverFetch } from './api';

export async function getDashboardMetrics() {
  try {
    const res = await serverFetch('/dashboard/metrics');
    if (!res.ok) return null;
    return await res.json();
  } catch (error) {
    console.error("Error fetching metrics:", error);
    return null;
  }
}

export async function getDashboardPeakHours() {
  try {
    const res = await serverFetch('/dashboard/peak-hours');
    if (!res.ok) return [];
    return await res.json();
  } catch (error) {
    console.error("Error fetching peak hours:", error);
    return [];
  }
}

export async function getDashboardRevenueTrends() {
  try {
    const res = await serverFetch('/dashboard/revenue-trends');
    if (!res.ok) return [];
    return await res.json();
  } catch (error) {
    console.error("Error fetching revenue trends:", error);
    return [];
  }
}

export async function getDashboardDemographics() {
  try {
    const res = await serverFetch('/dashboard/demographics');
    if (!res.ok) return { colors: [], models: [] };
    return await res.json();
  } catch (error) {
    console.error("Error fetching demographics:", error);
    return { colors: [], models: [] };
  }
}

export async function getDashboardPaymentInsights() {
  try {
    const res = await serverFetch('/dashboard/payment-insights');
    if (!res.ok) return { methods: [], overdue_revenue: 0 };
    return await res.json();
  } catch (error) {
    console.error("Error fetching payment insights:", error);
    return { methods: [], overdue_revenue: 0 };
  }
}
