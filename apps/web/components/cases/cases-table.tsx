'use client'

import { useQuery } from '@tanstack/react-query'
import Link from 'next/link'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Skeleton } from '@/components/ui/skeleton'
import { fetchCases, type CasePage } from '@/lib/api/cases'
import { CaseStatusBadge } from './case-status-badge'
import { CaseRowActions } from './case-row-actions'
import { EmptyState } from '@/components/shared/empty-state'
import { RelativeDate } from '@/components/shared/relative-date'

interface Props {
  initialData?: CasePage | undefined
  archived?: 'false' | 'true' | 'all'
}

export function CasesTable({ initialData, archived = 'false' }: Props) {
  const { data, isLoading } = useQuery({
    queryKey: ['cases', { archived }],
    queryFn: () => fetchCases({ archived }),
    initialData,
    staleTime: 30_000,
  })

  if (isLoading && !data) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-12 w-full rounded-md" />
        ))}
      </div>
    )
  }

  const items = data?.items ?? []

  if (items.length === 0) {
    return (
      <EmptyState
        title="Aucun dossier"
        description={
          archived === 'false'
            ? 'Créez votre premier dossier pour commencer.'
            : 'Aucun dossier archivé.'
        }
      />
    )
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Nom</TableHead>
          <TableHead>Référence</TableHead>
          <TableHead>Statut</TableHead>
          <TableHead>Créé le</TableHead>
          <TableHead className="w-10" />
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((c) => (
          <TableRow key={c.id}>
            <TableCell>
              <Link href={`/cases/${c.id}`} className="font-medium hover:underline">
                {c.name}
              </Link>
            </TableCell>
            <TableCell className="text-muted-foreground">{c.reference ?? '—'}</TableCell>
            <TableCell>
              <CaseStatusBadge archivedAt={c.archived_at} />
            </TableCell>
            <TableCell className="text-muted-foreground">
              <RelativeDate date={c.created_at} />
            </TableCell>
            <TableCell>
              <CaseRowActions caseItem={c} />
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
