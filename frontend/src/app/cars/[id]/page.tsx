import { getCarDetails } from '@/app/actions/cars';
import CarDetails from '@/components/cars/car-details';
import { AppSidebarWrapper } from '@/components/sidebar/app-sidebar-wrapper';
import { Header } from '@/components/sidebar/header';
import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar';

export const metadata = {
  title: 'Car Details | SmartPark OS',
};

// Next.js 15+ Async params parsing
export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = await params;
  
  // Securely query backend during render
  const sessionData = await getCarDetails(resolvedParams.id);
  
  return (
    <SidebarProvider>
      <AppSidebarWrapper />
      <SidebarInset className="flex flex-col min-h-screen">
        <Header title="Cars Directory" subTitle={`Session ${resolvedParams.id}`} />
        <CarDetails initialSession={sessionData} id={resolvedParams.id} />
      </SidebarInset>
    </SidebarProvider>
  );
}
