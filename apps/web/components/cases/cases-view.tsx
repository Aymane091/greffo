'use client'

import { useCallback, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { Plus, Search } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useDebounce } from '@/lib/hooks/use-debounce'
import { CasesTable } from './cases-table'
import { CaseFormDialog } from './case-form-dialog'
import type { CasePage } from '@/lib/api/cases'

type ArchivedFilter = 'false' | 'true' | 'all'

const TABS: { value: ArchivedFilter; label: string }[] = [
  { value: 'false', label: 'Actifs' },
  { value: 'true', label: 'Archivés' },
  { value: 'all', label: 'Tous' },
]

interface Props {
  initialData?: CasePage | undefined
}

export function CasesView({ initialData }: Props) {
  const router = useRouter()
  const searchParams = useSearchParams()

  const archived = (searchParams.get('archived') as ArchivedFilter) ?? 'false'
  const [search, setSearch] = useState(searchParams.get('q') ?? '')
  const debouncedSearch = useDebounce(search, 300)
  const [createOpen, setCreateOpen] = useState(false)

  const setTab = useCallback(
    (value: ArchivedFilter) => {
      const params = new URLSearchParams(searchParams.toString())
      params.set('archived', value)
      params.delete('q')
      setSearch('')
      router.push(`/cases?${params.toString()}`)
    },
    [router, searchParams],
  )

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        {/* 3-state toggle */}
        <div className="flex gap-1 rounded-lg border p-1 text-sm">
          {TABS.map(({ value, label }) => (
            <button
              key={value}
              className={cn(
                'rounded px-3 py-1 transition-colors',
                archived === value
                  ? 'bg-background shadow-sm font-medium'
                  : 'text-muted-foreground hover:text-foreground',
              )}
              onClick={() => setTab(value)}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Search */}
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            className="pl-8"
            placeholder="Rechercher un dossier..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <Button size="sm" onClick={() => setCreateOpen(true)}>
          <Plus className="mr-1.5 h-4 w-4" />
          Nouveau dossier
        </Button>
      </div>

      <CasesTable
        archived={archived}
        query={debouncedSearch || undefined}
        initialData={archived === 'false' && !debouncedSearch ? initialData : undefined}
      />

      <CaseFormDialog open={createOpen} onOpenChange={setCreateOpen} />
    </div>
  )
}
