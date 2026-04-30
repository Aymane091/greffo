import { notFound } from 'next/navigation'
import { auth } from '@/lib/auth'
import { apiFetch } from '@/lib/api-client'
import { CaseStatusBadge } from '@/components/cases/case-status-badge'
import { RelativeDate } from '@/components/shared/relative-date'
import type { CaseItem } from '@/lib/api/cases'

type Props = { params: Promise<{ id: string }> }

export default async function CaseDetailPage({ params }: Props) {
  const { id } = await params
  const session = await auth()

  let caseData: CaseItem
  try {
    const res = await apiFetch(`/api/v1/cases/${id}`, session!)
    caseData = await res.json()
  } catch {
    notFound()
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-bold">{caseData!.name}</h1>
        <CaseStatusBadge archivedAt={caseData!.archived_at} />
      </div>

      <dl className="grid gap-4 sm:grid-cols-2 text-sm">
        {caseData!.reference && (
          <div className="space-y-1">
            <dt className="font-medium text-muted-foreground">Référence</dt>
            <dd>{caseData!.reference}</dd>
          </div>
        )}
        <div className="space-y-1">
          <dt className="font-medium text-muted-foreground">Créé le</dt>
          <dd>
            <RelativeDate date={caseData!.created_at} />
          </dd>
        </div>
        {caseData!.description && (
          <div className="col-span-2 space-y-1">
            <dt className="font-medium text-muted-foreground">Description</dt>
            <dd className="whitespace-pre-wrap">{caseData!.description}</dd>
          </div>
        )}
      </dl>
    </div>
  )
}
