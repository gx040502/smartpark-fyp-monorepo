import MetricsCards from '@/components/dashboard/MetricsCards';
import PeakHoursChart from '@/components/dashboard/PeakHoursChart';
import RevenueTrendsChart from '@/components/dashboard/RevenueTrendsChart';
import LiveCameraSimulation from '@/components/dashboard/LiveCameraSimulation';
import ExitAlerts from '@/components/dashboard/ExitAlerts';

export default function Dashboard({ 
  metrics, 
  peakHours, 
  revenueTrends 
}: { 
  metrics: any, 
  peakHours: any, 
  revenueTrends: any 
}) {
  return (
    <div className="p-6 md:p-8 flex-1 space-y-6 bg-slate-50 border-t min-h-[calc(100vh-64px)] animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-gray-900">Dashboard Overview</h1>
        <p className="text-muted-foreground mt-1">
          Monitor live analytics, occupancy status, and system alerts.
        </p>
      </div>

      <MetricsCards initialData={metrics} />
      
      <ExitAlerts />

      <div className="grid gap-6 md:grid-cols-3">
        <PeakHoursChart initialData={peakHours} />
        <RevenueTrendsChart initialData={revenueTrends} />
      </div>

      <LiveCameraSimulation />
    </div>
  );
}
