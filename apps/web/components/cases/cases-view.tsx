'use client'

import { useState } from 'react'
import { Plus } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { CasesTable } from './cases-table'
import { CaseFormDialog } from './case-form-dialog'
import type { CasePage } from '@/lib/api/cases'

type Tab = 'active' | 'archived'

interface Props {
  initialData?: CasePage | undefined
}

export function CasesView({ initialData }: Props) {
  const [tab, setTab] = useState<Tab>('active')
  const [createOpen, setCreateOpen] = useState(false)

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex gap-1 rounded-lg border p-1 text-sm">
          <button
            className={cn(
              'rounded px-3 py-1 transition-colors',
              tab === 'active'
                ? 'bg-background shadow-sm font-medium'
                : 'text-muted-foreground hover:text-foreground',
            )}
            onClick={() => setTab('active')}
          >
            Actifs
          </button>
          <button
            className={cn(
              'rounded px-3 py-1 transition-colors',
              tab === 'archived'
                ? 'bg-background shadow-sm font-medium'
                : 'text-muted-foreground hover:text-foreground',
            )}
            onClick={() => setTab('archived')}
          >
            Archivés
          </button>
        </div>
        <Button size="sm" onClick={() => setCreateOpen(true)}>
          <Plus className="mr-1.5 h-4 w-4" />
          Nouveau dossier
        </Button>
      </div>

      <CasesTable
        archived={tab === 'active' ? 'false' : 'true'}
        initialData={tab === 'active' ? initialData : undefined}
      />

      <CaseFormDialog open={createOpen} onOpenChange={setCreateOpen} />
    </div>
  )
}
