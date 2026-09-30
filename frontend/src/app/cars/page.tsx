import { getCars, getCarFilterOptions } from '@/app/actions/cars';
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
  
  // Fetch car data and filter options in parallel
  const [carPayload, filterOptions] = await Promise.all([
    getCars({
      page: resolvedParams.page,
      search: resolvedParams.search,
      color: resolvedParams.color,
      model: resolvedParams.model,
      status: resolvedParams.status,
      date_from: resolvedParams.date_from,
      date_to: resolvedParams.date_to,
      date_field: resolvedParams.date_field,
      time_from: resolvedParams.time_from,
      time_to: resolvedParams.time_to,
    }),
    getCarFilterOptions(),
  ]);

  return (
    <SidebarProvider>
      <AppSidebarWrapper />
      <SidebarInset className="flex flex-col min-h-screen">
        <Header title="Cars Directory" />
        <CarList
          initialData={carPayload}
          searchParams={resolvedParams}
          filterOptions={filterOptions}
        />
      </SidebarInset>
    </SidebarProvider>
  );
}
