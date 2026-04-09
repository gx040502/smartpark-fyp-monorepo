'use client';

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Car, CreditCard, Clock } from 'lucide-react';

export default function MetricsCards({ initialData }: { initialData: any }) {
  const metrics = initialData;

  if (!metrics) {
    return <div className="grid gap-4 md:grid-cols-3 mb-6 animate-pulse">
      {/* Loading placeholders */}
      {[1, 2, 3].map(i => <Card key={i}><CardHeader className="h-14"></CardHeader><CardContent className="h-20"></CardContent></Card>)}
    </div>;
  }

  return (
    <div className="grid gap-4 md:grid-cols-3 mb-6">
      <Card className="bg-gradient-to-br from-blue-500 to-blue-600 text-white border-none shadow-lg">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle>Current Occupancy</CardTitle>
          <Car className="h-5 w-5 opacity-75" />
        </CardHeader>
        <CardContent>
          <div className="text-3xl font-bold">{metrics.occupancy.current}</div>
          <CardDescription className="text-xs mt-1 text-white opacity-90">
            {metrics.occupancy.total_completed} cars have exited today
          </CardDescription>
        </CardContent>
      </Card>

      <Card className="bg-gradient-to-br from-emerald-500 to-emerald-600 text-white border-none shadow-lg">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle>Total Daily Revenue</CardTitle>
          <CreditCard className="h-5 w-5 opacity-75" />
        </CardHeader>
        <CardContent>
          <div className="text-3xl font-bold">RM {parseFloat(metrics.daily_revenue).toFixed(2)}</div>
          <CardDescription className="text-xs mt-1 text-white opacity-90">
            Total sums derived from completed sessions
          </CardDescription>
        </CardContent>
      </Card>

      <Card className="bg-gradient-to-br from-indigo-500 to-indigo-600 text-white border-none shadow-lg">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium opacity-90">Avg. Dwell Time</CardTitle>
          <Clock className="h-5 w-5 opacity-75" />
        </CardHeader>
        <CardContent>
          <div className="text-3xl font-bold">{metrics.avg_dwell_time}</div>
          <CardDescription className="text-xs mt-1 text-white opacity-90">
            Average duration per parking session
          </CardDescription>
        </CardContent>
      </Card>
    </div>
  );
}
