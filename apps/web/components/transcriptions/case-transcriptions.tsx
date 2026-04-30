'use client'

import { useQuery } from '@tanstack/react-query'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/shared/empty-state'
import { RelativeDate } from '@/components/shared/relative-date'
import { TranscriptionStatusBadge } from './transcription-status-badge'
import { fetchCaseTranscriptions, type TranscriptionPage } from '@/lib/api/transcriptions'
import { formatDuration } from '@/lib/format'

interface Props {
  caseId: string
  initialData?: TranscriptionPage | undefined
}

export function CaseTranscriptions({ caseId, initialData }: Props) {
  const { data, isLoading } = useQuery({
    queryKey: ['case-transcriptions', caseId],
    queryFn: () => fetchCaseTranscriptions(caseId),
    initialData,
    staleTime: 30_000,
  })

  const items = data?.items ?? []
  const total = data?.total ?? 0

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">
          Transcriptions{' '}
          <span className="text-sm font-normal text-muted-foreground">({total})</span>
        </h2>
        <span title="Bientôt disponible — Ticket 13b">
          <Button size="sm" disabled aria-label="Nouvelle transcription (bientôt disponible)">
            Nouvelle transcription
          </Button>
        </span>
      </div>

      {isLoading && !data ? (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full rounded-md" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <EmptyState title="Aucune transcription dans ce dossier." />
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Nom</TableHead>
              <TableHead>Statut</TableHead>
              <TableHead>Durée</TableHead>
              <TableHead>Créée le</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((tr) => (
              <TableRow key={tr.id} className="cursor-pointer hover:bg-muted/50">
                <TableCell className="font-medium">{tr.title ?? '—'}</TableCell>
                <TableCell>
                  <TranscriptionStatusBadge status={tr.status} />
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {tr.audio_duration_s != null
                    ? formatDuration(tr.audio_duration_s)
                    : '—'}
                </TableCell>
                <TableCell className="text-muted-foreground">
                  <RelativeDate date={tr.created_at} />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </section>
  )
}
