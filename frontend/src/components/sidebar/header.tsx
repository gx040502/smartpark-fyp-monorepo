import { SidebarTrigger } from "@/components/ui/sidebar"
import { Separator } from "@/components/ui/separator"

interface HeaderProps {
  title: string
  subTitle?: string
}

export function Header({ title, subTitle }: HeaderProps) {
  return (
    <header className="flex h-16 shrink-0 items-center justify-between gap-2 border-b bg-white px-6 shadow-sm sticky top-0 z-10 w-full transition-[width,height] ease-linear group-has-[[data-collapsible=icon]]/sidebar-wrapper:h-12">
      <div className="flex items-center gap-2">
        <SidebarTrigger className="-ml-1 text-gray-500 hover:bg-gray-100 p-2" />
        <Separator orientation="vertical" className="mr-2 h-4" />
        <div className="flex items-center gap-2 font-medium text-gray-800 text-sm">
          <span>{title}</span>
          {subTitle && (
            <>
              <span className="text-gray-400">/</span>
              <span className="text-gray-500 font-normal">{subTitle}</span>
            </>
          )}
        </div>
      </div>
    </header>
  )
}
