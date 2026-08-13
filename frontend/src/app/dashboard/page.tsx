import Dashboard from '@/components/dashboards/dashboard';
import { AppSidebarWrapper } from '@/components/sidebar/app-sidebar-wrapper';
import { Header } from '@/components/sidebar/header';
import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar';
import { 
  getDashboardMetrics, 
  getDashboardPeakHours, 
  getDashboardRevenueTrends,
  getDashboardDemographics,
  getDashboardPaymentInsights
} from '@/app/actions/dashboard';

export const metadata = {
  title: 'Dashboard | SmartPark OS',
  description: 'Smart Parking Management System Analytics',
};

export default async function Page() {
  const [metrics, peakHours, revenueTrends, demographics, paymentInsights] = await Promise.all([
    getDashboardMetrics(),
    getDashboardPeakHours(),
    getDashboardRevenueTrends(),
    getDashboardDemographics(),
    getDashboardPaymentInsights()
  ]);

  return (
    <SidebarProvider>
      <AppSidebarWrapper />
      <SidebarInset className="bg-slate-50 flex flex-col min-h-screen">
        <Header title="Dashboard" />
        <Dashboard 
          metrics={metrics} 
          peakHours={peakHours} 
          revenueTrends={revenueTrends} 
          demographics={demographics}
          paymentInsights={paymentInsights}
        />
      </SidebarInset>
    </SidebarProvider>
  );
}
