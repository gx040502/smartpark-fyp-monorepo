"use client"

import * as React from "react"
import { Car, LayoutDashboard, MessageSquare, UserCircle, LogOut } from "lucide-react"

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar"
import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"

export function AppSidebarWrapper({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const pathname = usePathname()
  const { toggleSidebar } = useSidebar()

  const router = useRouter()

  const navItems = [
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { name: 'Cars Directory', href: '/cars', icon: Car },
    { name: 'AI Agent', href: '/ai-agent', icon: MessageSquare },
    { name: 'Profile', href: '/profile', icon: UserCircle },
  ]

  const handleLogout = () => {
    localStorage.removeItem('auth_token')
    window.location.href = '/login'
  }

  return (
    <Sidebar variant="inset" {...props}>
      <SidebarHeader className="flex flex-row items-center gap-2 p-4 pt-6 text-indigo-700">
        <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-indigo-600 text-white">
          <Car className="size-5" />
        </div>
        <span className="font-semibold text-xl tracking-tight">SmartPark OS</span>
      </SidebarHeader>
      <SidebarContent className="px-2 mt-4 space-y-1">
        <SidebarMenu>
          {navItems.map((item) => {
            const isActive = pathname.startsWith(item.href)
            return (
              <SidebarMenuItem key={item.name}>
                <SidebarMenuButton 
                  isActive={isActive}
                  className={`h-11 rounded-lg px-4 ${isActive ? 'bg-indigo-50 text-indigo-700 font-medium' : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'}`}
                  onClick={() => router.push(item.href)}
                >
                    <item.icon className={`h-5 w-5 ${isActive ? 'text-indigo-600' : 'text-gray-500'}`} />
                    <span className="ml-2">{item.name}</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            )
          })}
        </SidebarMenu>
      </SidebarContent>
      <SidebarFooter className="p-4 mb-2">
        <div className="flex items-center gap-3 bg-gray-50 p-3 rounded-xl mb-4 border border-gray-100">
          <Avatar className="h-9 w-9 border">
            <AvatarImage src="https://i.pravatar.cc/150?u=admin" />
            <AvatarFallback>AD</AvatarFallback>
          </Avatar>
          <div className="flex flex-col overflow-hidden">
            <span className="text-sm font-semibold truncate leading-tight">Admin System</span>
            <span className="text-xs text-muted-foreground truncate">admin@smartpark.com</span>
          </div>
        </div>
        
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton 
              onClick={handleLogout}
              className="h-10 text-red-600 hover:text-red-700 hover:bg-red-50 rounded-lg"
            >
              <LogOut className="h-5 w-5 mr-2" />
              <span>Logout</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  )
}
