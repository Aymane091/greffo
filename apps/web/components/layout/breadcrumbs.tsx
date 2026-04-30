'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { ChevronRight } from 'lucide-react'

const LABELS: Record<string, string> = {
  dashboard: 'Tableau de bord',
  cases: 'Dossiers',
}

export function Breadcrumbs() {
  const pathname = usePathname()
  const segments = pathname.split('/').filter(Boolean)

  const crumbs = segments.map((seg, i) => ({
    href: '/' + segments.slice(0, i + 1).join('/'),
    label: LABELS[seg] ?? seg,
  }))

  if (crumbs.length <= 1) {
    return <span className="text-sm font-medium">{crumbs[0]?.label}</span>
  }

  return (
    <nav className="flex items-center gap-1 text-sm">
      {crumbs.map((crumb, i) => (
        <span key={crumb.href} className="flex items-center gap-1">
          {i > 0 && <ChevronRight className="h-3 w-3 text-muted-foreground" />}
          {i === crumbs.length - 1 ? (
            <span className="font-medium">{crumb.label}</span>
          ) : (
            <Link href={crumb.href} className="text-muted-foreground hover:text-foreground">
              {crumb.label}
            </Link>
          )}
        </span>
      ))}
    </nav>
  )
}
