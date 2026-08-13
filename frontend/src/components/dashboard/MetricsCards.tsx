'use client';

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Car, CreditCard, Clock } from 'lucide-react';

export default function MetricsCards({ initialData, paymentInsights }: { initialData: any, paymentInsights: any }) {
  const metrics = initialData;

  if (!metrics || !paymentInsights) {
    return <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-6 animate-pulse">
      {/* Loading placeholders */}
      {[1, 2, 3, 4].map(i => <Card key={i}><CardHeader className="h-14"></CardHeader><CardContent className="h-20"></CardContent></Card>)}
    </div>;
  }

  const { current, paid, total_completed } = metrics.occupancy;
  const totalActive = current + paid + total_completed;

  // Percentages for the funnel
  const currentPct = totalActive > 0 ? (current / totalActive) * 100 : 0;
  const paidPct = totalActive > 0 ? (paid / totalActive) * 100 : 0;
  const completedPct = totalActive > 0 ? (total_completed / totalActive) * 100 : 0;

  return (
    <div className="space-y-6 mb-6">
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card className="bg-gradient-to-br from-blue-500 to-blue-600 text-white border-none shadow-lg">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle>Today Occupancy</CardTitle>
            <Car className="h-5 w-5 opacity-75" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{totalActive}</div>
            <CardDescription className="text-xs mt-1 text-white opacity-90">
              Total cars parked (Shopping + Exiting)
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

        <Card className="bg-gradient-to-br from-amber-500 to-amber-600 text-white border-none shadow-lg">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle>Overdue Revenue</CardTitle>
            <CreditCard className="h-5 w-5 opacity-75" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">RM {parseFloat(paymentInsights.overdue_revenue).toFixed(2)}</div>
            <CardDescription className="text-xs mt-1 text-white opacity-90">
              Revenue from additional grace period overstays
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

      <Card className="border-gray-200 shadow-sm overflow-hidden">
        <CardContent className="p-0">
          <div className="bg-white px-6 py-4 flex flex-col md:flex-row items-center justify-between gap-4 border-b">
            <div>
              <h3 className="font-semibold text-gray-900">Live Status Funnel</h3>
              <p className="text-sm text-gray-500">Real-time breakdown of currently active vehicles</p>
            </div>
            <div className="flex gap-6 text-sm">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-blue-500"></div>
                <span className="text-gray-600">Shopping: <span className="font-bold text-gray-900">{current}</span></span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-emerald-500"></div>
                <span className="text-gray-600">Ready to Exit: <span className="font-bold text-gray-900">{paid}</span></span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-gray-300"></div>
                <span className="text-gray-600">Exited Today: <span className="font-bold text-gray-900">{total_completed}</span></span>
              </div>
            </div>
          </div>

          <div className="p-6 bg-slate-50">
            {totalActive === 0 ? (
              <div className="h-8 w-full flex items-center justify-center rounded-full bg-gray-100 text-xs font-medium text-gray-400 shadow-inner">
                No active vehicles
              </div>
            ) : (
              <div className="h-8 w-full flex rounded-full overflow-hidden shadow-inner bg-gray-100">
                <div
                  className="bg-blue-500 h-full transition-all duration-1000 ease-out flex items-center justify-center text-xs font-bold text-white shadow-[inset_0_-2px_4px_rgba(0,0,0,0.1)]"
                  style={{ width: `${currentPct}%` }}
                >
                  {currentPct > 10 && 'Shopping'}
                </div>
                <div
                  className="bg-emerald-500 h-full transition-all duration-1000 ease-out flex items-center justify-center text-xs font-bold text-white shadow-[inset_0_-2px_4px_rgba(0,0,0,0.1)]"
                  style={{ width: `${paidPct}%` }}
                >
                  {paidPct > 10 && 'Ready'}
                </div>
                <div
                  className="bg-gray-300 h-full transition-all duration-1000 ease-out flex items-center justify-center text-xs font-bold text-gray-700 shadow-[inset_0_-2px_4px_rgba(0,0,0,0.05)]"
                  style={{ width: `${completedPct}%` }}
                >
                  {completedPct > 10 && 'Exited'}
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
