import { getCars } from '@/app/actions/cars';
import CarList from '@/components/cars/car-list';
import { AppSidebarWrapper } from '@/components/sidebar/app-sidebar-wrapper';
import { Header } from '@/components/sidebar/header';
import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar';

export const metadata = {
  title: 'Cars Directory | SmartPark OS',
};

export default async function Page({ 
  searchParams 
}: { 
  searchParams: Promise<{ [key: string]: string | undefined }> 
}) {
  const resolvedParams = await searchParams;
  
  // Cleanly await server data before the page mounts!
  const carPayload = await getCars({
    page: resolvedParams.page,
    search: resolvedParams.search,
    color: resolvedParams.color,
    status: resolvedParams.status
  });

  return (
    <SidebarProvider>
      <AppSidebarWrapper />
      <SidebarInset className="flex flex-col min-h-screen">
        <Header title="Cars Directory" />
        {/* Pass strictly queried data sequentially below */}
        <CarList initialData={carPayload} searchParams={resolvedParams} />
      </SidebarInset>
    </SidebarProvider>
  );
}
