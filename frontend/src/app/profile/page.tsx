import ProfileForm from '@/components/profile/profile-form';
import { AppSidebarWrapper } from '@/components/sidebar/app-sidebar-wrapper';
import { Header } from '@/components/sidebar/header';
import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar';

export const metadata = {
  title: 'Profile | SmartPark OS',
};

export default function Page() {
  return (
    <SidebarProvider>
      <AppSidebarWrapper />
      <SidebarInset className="flex flex-col min-h-screen">
        <Header title="Settings" subTitle="Profile" />
        <ProfileForm />
      </SidebarInset>
    </SidebarProvider>
  );
}
