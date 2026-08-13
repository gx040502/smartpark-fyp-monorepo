import ExitAlerts from '@/components/dashboard/ExitAlerts';
import { AppSidebarWrapper } from '@/components/sidebar/app-sidebar-wrapper';
import { Header } from '@/components/sidebar/header';
import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar';

export const metadata = {
  title: 'Exit Gate Alerts | SmartPark OS',
};

export default function Page() {
  return (
    <SidebarProvider>
      <AppSidebarWrapper />
      <SidebarInset className="flex flex-col min-h-screen">
        <Header title="Exit Gate Alerts" />
        <div className="p-6 md:p-8 flex-1 bg-slate-50 border-t min-h-[calc(100vh-64px)] animate-in fade-in slide-in-from-bottom-4 duration-500">
          <ExitAlerts />
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
}
