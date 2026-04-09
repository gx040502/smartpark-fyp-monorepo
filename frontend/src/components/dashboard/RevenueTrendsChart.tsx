'use client';

import dynamic from 'next/dynamic';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

// Dynamically import ReactApexChart
const Chart = dynamic(() => import('react-apexcharts'), { ssr: false });

export default function RevenueTrendsChart({ initialData }: { initialData: any[] }) {
  // Use data prefetched explicitly from the server wrapper
  const data = initialData || [];

  const chartOptions: ApexCharts.ApexOptions = {
    chart: { type: 'bar', toolbar: { show: false } },
    colors: ['#22c55e'], // Green for revenue
    plotOptions: { bar: { borderRadius: 4, columnWidth: '60%' } },
    dataLabels: { enabled: false },
    xaxis: { categories: data.map(d => d.day) },
    yaxis: { labels: { formatter: (val) => `RM ${val}` } },
    tooltip: { 
      y: { formatter: (val) => `RM ${val.toFixed(2)}` }
    }
  };

  const chartSeries = [
    { name: 'Revenue', data: data.map(d => d.revenue) }
  ];

  return (
    <Card className="col-span-1">
      <CardHeader>
        <CardTitle className="text-xl font-bold">Revenue Trends (7 Days)</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[300px]">
          {data.length > 0 ? (
            <Chart options={chartOptions} series={chartSeries} type="bar" height="100%" />
          ) : (
            <div className="flex h-full items-center justify-center text-muted-foreground">Loading chart data...</div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
