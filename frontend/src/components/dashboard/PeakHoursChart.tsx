'use client';

import dynamic from 'next/dynamic';
import { useEffect, useState } from 'react';
import { apiFetch } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import Flatpickr from 'react-flatpickr';
import "flatpickr/dist/themes/light.css";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

// Dynamically import ReactApexChart to avoid SSR issues
const Chart = dynamic(() => import('react-apexcharts'), { ssr: false });

export default function PeakHoursChart({ initialData }: { initialData: any[] }) {
  const [data, setData] = useState<any[]>(initialData || []);
  const [filter, setFilter] = useState('today');
  const [dateRange, setDateRange] = useState<Date[]>([]);
  
  useEffect(() => {
    // Only re-fetch if filter changes away from the initial 'today' SSR payload
    if (filter === 'today' && dateRange.length === 0) return;
    fetchData();
  }, [filter, dateRange]);

  const fetchData = async () => {
    try {
      let query = `?filter=${filter}`;
      
      if (filter === 'custom' && dateRange.length === 2) {
        const start = dateRange[0].toISOString().split('T')[0];
        const end = dateRange[1].toISOString().split('T')[0];
        query = `?filter=custom&start_date=${start}&end_date=${end}`;
      } else if (filter === 'custom') {
        return; // Don't fetch if custom range is incomplete
      }

      // Backward compatibility for client-side fetches utilizing intercepted tokens
      const res = await apiFetch(`/dashboard/peak-hours${query}`);
      if (res.ok) {
        const json = await res.json();
        setData(json);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const chartOptions: ApexCharts.ApexOptions = {
    chart: { type: 'line', toolbar: { show: false }, zoom: { enabled: false } },
    stroke: { curve: 'smooth', width: 3 },
    colors: ['#3b82f6', '#ef4444'], // Blue for entries, Red for exits
    xaxis: { categories: data.map(d => d.hour) },
    legend: { position: 'top' },
    tooltip: { shared: true, intersect: false }
  };

  const chartSeries = [
    { name: 'Entries', data: data.map(d => d.entries) },
    { name: 'Exits', data: data.map(d => d.exits) }
  ];

  return (
    <Card className="col-span-1 md:col-span-2">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-xl font-bold">Peak Hours Analysis</CardTitle>
        <div className="flex space-x-2 items-center">
          <Select value={filter} onValueChange={(val) => setFilter(val || 'today')}>
            <SelectTrigger className="w-[130px]">
              <SelectValue placeholder="Select period" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="today">Today</SelectItem>
              <SelectItem value="week">This Week</SelectItem>
              <SelectItem value="custom">Custom Range</SelectItem>
            </SelectContent>
          </Select>
          
          {filter === 'custom' && (
            <div className="w-[220px]">
              <Flatpickr
                options={{ mode: 'range', dateFormat: 'Y-m-d' }}
                value={dateRange}
                onChange={(dates: Date[]) => setDateRange(dates)}
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                placeholder="Select Date Range"
              />
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="h-[300px]">
          {data.length > 0 ? (
            <Chart options={chartOptions} series={chartSeries} type="line" height="100%" />
          ) : (
            <div className="flex h-full items-center justify-center text-muted-foreground">Loading chart data...</div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
