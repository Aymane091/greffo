import { redirect } from 'next/navigation'
import { auth } from '@/lib/auth'
import { AppSidebar } from '@/components/layout/app-sidebar'
import { UserMenu } from '@/components/layout/user-menu'
import { Breadcrumbs } from '@/components/layout/breadcrumbs'

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const session = await auth()
  if (!session?.userId) redirect('/login')

  return (
    <div className="flex h-screen overflow-hidden">
      <AppSidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex h-14 shrink-0 items-center justify-between border-b px-4">
          <Breadcrumbs />
          <UserMenu email={session.user?.email ?? ''} />
        </header>
        <main className="flex-1 overflow-auto p-6">{children}</main>
      </div>
    </div>
  )
}
