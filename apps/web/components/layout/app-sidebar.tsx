'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { LayoutDashboard, FolderOpen, ChevronLeft, ChevronRight } from 'lucide-react'
import { cn } from '@/lib/utils'

const STORAGE_KEY = 'greffo:sidebar-collapsed'

const navItems = [
  { href: '/dashboard', label: 'Tableau de bord', icon: LayoutDashboard },
  { href: '/cases', label: 'Dossiers', icon: FolderOpen },
]

export function AppSidebar() {
  const [collapsed, setCollapsed] = useState(false)
  const pathname = usePathname()

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored !== null) setCollapsed(stored === 'true')
  }, [])

  function toggle() {
    setCollapsed((c) => {
      const next = !c
      localStorage.setItem(STORAGE_KEY, String(next))
      return next
    })
  }

  return (
    <aside
      className={cn(
        'flex flex-col border-r bg-sidebar transition-all duration-200',
        collapsed ? 'w-14' : 'w-56',
      )}
    >
      <div className="flex h-14 shrink-0 items-center border-b px-3">
        {!collapsed && <span className="text-lg font-semibold tracking-tight">Greffo</span>}
      </div>

      <nav className="flex-1 space-y-1 p-2">
        {navItems.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              'flex items-center gap-3 rounded-md px-2 py-2 text-sm transition-colors',
              pathname === href || pathname.startsWith(href + '/')
                ? 'bg-sidebar-accent text-sidebar-accent-foreground font-medium'
                : 'text-sidebar-foreground hover:bg-sidebar-accent/60',
            )}
          >
            <Icon className="h-4 w-4 shrink-0" />
            {!collapsed && label}
          </Link>
        ))}
      </nav>

      <button
        onClick={toggle}
        className="flex h-10 shrink-0 items-center justify-center border-t text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
        aria-label={collapsed ? 'Déplier la barre latérale' : 'Replier la barre latérale'}
      >
        {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
      </button>
    </aside>
  )
}
