import { notFound } from 'next/navigation'
import Link from 'next/link'
import { ChevronRight } from 'lucide-react'
import { auth } from '@/lib/auth'
import { apiFetch, ApiError } from '@/lib/api-client'
import { Separator } from '@/components/ui/separator'
import { TranscriptionStatusBadge } from '@/components/transcriptions/transcription-status-badge'
import { RelativeDate } from '@/components/shared/relative-date'
import { formatDuration } from '@/lib/format'
import type { TranscriptionItem } from '@/lib/api/transcriptions'
import type { CaseItem } from '@/lib/api/cases'

async function fetchTranscription(
  id: string,
  session: { userId: string; organizationId: string },
): Promise<TranscriptionItem | null> {
  try {
    const res = await apiFetch(`/api/v1/transcriptions/${id}`, session)
    return res.json()
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null
    throw err
  }
}

async function fetchCase(
  id: string,
  session: { userId: string; organizationId: string },
): Promise<CaseItem | null> {
  try {
    const res = await apiFetch(`/api/v1/cases/${id}`, session)
    return res.json()
  } catch {
    return null
  }
}

export default async function TranscriptionDetailPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  const session = await auth()
  if (!session?.userId) notFound()

  const transcription = await fetchTranscription(id, session!)
  if (!transcription) notFound()

  const parentCase = transcription.case_id
    ? await fetchCase(transcription.case_id, session!)
    : null

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-1 text-sm text-muted-foreground">
        <Link href="/cases" className="hover:text-foreground">
          Dossiers
        </Link>
        <ChevronRight className="h-3 w-3" />
        {parentCase ? (
          <Link href={`/cases/${parentCase.id}`} className="hover:text-foreground">
            {parentCase.name}
          </Link>
        ) : (
          <span>Dossier</span>
        )}
        <ChevronRight className="h-3 w-3" />
        <span className="font-medium text-foreground">
          {transcription.title ?? 'Transcription'}
        </span>
      </nav>

      {/* Header */}
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-bold">
          {transcription.title ?? 'Transcription sans titre'}
        </h1>
        <TranscriptionStatusBadge status={transcription.status} />
      </div>

      {/* Metadata */}
      <dl className="grid gap-4 sm:grid-cols-2 text-sm">
        <div className="space-y-1">
          <dt className="font-medium text-muted-foreground">Durée audio</dt>
          <dd>
            {transcription.audio_duration_s != null
              ? formatDuration(transcription.audio_duration_s)
              : '—'}
          </dd>
        </div>
        <div className="space-y-1">
          <dt className="font-medium text-muted-foreground">Langue</dt>
          <dd>{transcription.language}</dd>
        </div>
        <div className="space-y-1">
          <dt className="font-medium text-muted-foreground">Créée le</dt>
          <dd>
            <RelativeDate date={transcription.created_at} />
          </dd>
        </div>
        <div className="space-y-1">
          <dt className="font-medium text-muted-foreground">Terminée le</dt>
          <dd>
            {transcription.processing_ended_at ? (
              <RelativeDate date={transcription.processing_ended_at} />
            ) : (
              '—'
            )}
          </dd>
        </div>
      </dl>

      <Separator />

      {/* Placeholder */}
      <div className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
        Détail complet en construction — Ticket 13b (lecteur audio + segments cliquables)
      </div>
    </div>
  )
}
