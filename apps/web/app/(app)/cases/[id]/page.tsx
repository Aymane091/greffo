'use client'

import { use, useState } from 'react'
import { notFound } from 'next/navigation'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Pencil, Archive, ArchiveRestore } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { CaseStatusBadge } from '@/components/cases/case-status-badge'
import { CaseFormDialog } from '@/components/cases/case-form-dialog'
import { CaseTranscriptions } from '@/components/transcriptions/case-transcriptions'
import { RelativeDate } from '@/components/shared/relative-date'
import { archiveCase, unarchiveCase } from '@/lib/api/cases'
import { toast } from 'sonner'

// This page is a client component so we can use hooks for Edit/Archive/Unarchive.
// The case data is fetched via TanStack Query (no SSR initialData needed for detail page).

async function fetchCase(id: string) {
  const res = await fetch(`/api/internal/cases/${id}`)
  if (res.status === 404) return null
  if (!res.ok) throw new Error('Failed to fetch case')
  return res.json()
}

export default function CaseDetailPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = use(params)
  const qc = useQueryClient()
  const [editOpen, setEditOpen] = useState(false)

  const { data: caseData, isLoading } = useQuery({
    queryKey: ['case', id],
    queryFn: () => fetchCase(id),
    staleTime: 30_000,
  })

  const archiveMut = useMutation({
    mutationFn: () => archiveCase(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['case', id] })
      qc.invalidateQueries({ queryKey: ['cases'] })
      toast.success('Dossier archivé')
    },
    onError: () => toast.error("Erreur lors de l'archivage"),
  })

  const unarchiveMut = useMutation({
    mutationFn: () => unarchiveCase(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['case', id] })
      qc.invalidateQueries({ queryKey: ['cases'] })
      toast.success('Dossier désarchivé')
    },
    onError: () => toast.error('Erreur lors du désarchivage'),
  })

  if (isLoading) {
    return <div className="text-sm text-muted-foreground">Chargement…</div>
  }

  if (!caseData) {
    notFound()
  }

  const isArchived = !!caseData.archived_at

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-bold">{caseData.name}</h1>
          <CaseStatusBadge archivedAt={caseData.archived_at} />
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => setEditOpen(true)}>
            <Pencil className="mr-1.5 h-4 w-4" />
            Modifier
          </Button>
          {isArchived ? (
            <Button
              variant="outline"
              size="sm"
              onClick={() => unarchiveMut.mutate()}
              disabled={unarchiveMut.isPending}
            >
              <ArchiveRestore className="mr-1.5 h-4 w-4" />
              Désarchiver
            </Button>
          ) : (
            <Button
              variant="outline"
              size="sm"
              onClick={() => archiveMut.mutate()}
              disabled={archiveMut.isPending}
            >
              <Archive className="mr-1.5 h-4 w-4" />
              Archiver
            </Button>
          )}
        </div>
      </div>

      {/* Metadata */}
      <dl className="grid gap-4 sm:grid-cols-2 text-sm">
        {caseData.reference && (
          <div className="space-y-1">
            <dt className="font-medium text-muted-foreground">Référence</dt>
            <dd>{caseData.reference}</dd>
          </div>
        )}
        <div className="space-y-1">
          <dt className="font-medium text-muted-foreground">Créé le</dt>
          <dd>
            <RelativeDate date={caseData.created_at} />
          </dd>
        </div>
        {caseData.description && (
          <div className="col-span-2 space-y-1">
            <dt className="font-medium text-muted-foreground">Description</dt>
            <dd className="whitespace-pre-wrap">{caseData.description}</dd>
          </div>
        )}
      </dl>

      <Separator />

      {/* Transcriptions */}
      <CaseTranscriptions caseId={id} />

      {/* Edit dialog */}
      <CaseFormDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        mode="edit"
        initialValues={caseData}
      />
    </div>
  )
}
