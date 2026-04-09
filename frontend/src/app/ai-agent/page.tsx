import AIAgentMockup from '@/components/ai-agent/ai-agent-mockup';
import { AppSidebarWrapper } from '@/components/sidebar/app-sidebar-wrapper';
import { Header } from '@/components/sidebar/header';
import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar';

export const metadata = {
  title: 'AI Agent | SmartPark OS',
};

export default function Page() {
  return (
    <SidebarProvider>
      <AppSidebarWrapper />
      <SidebarInset className="flex flex-col min-h-screen bg-slate-50">
        <Header title="AI Operations" subTitle="Assistant" />
        <AIAgentMockup />
      </SidebarInset>
    </SidebarProvider>
  );
}
