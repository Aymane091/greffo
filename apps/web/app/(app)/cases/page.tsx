import { auth } from '@/lib/auth'
import { apiFetch } from '@/lib/api-client'
import { CasesView } from '@/components/cases/cases-view'
import type { CasePage } from '@/lib/api/cases'

export default async function CasesPage() {
  const session = await auth()

  let initialData: CasePage | undefined
  try {
    const res = await apiFetch('/api/v1/cases?archived=false&size=50', session!)
    initialData = await res.json()
  } catch {
    // SSR fails gracefully — client will refetch
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Dossiers</h1>
      <CasesView initialData={initialData} />
    </div>
  )
}
