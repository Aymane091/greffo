import { auth } from '@/lib/auth'
import { apiFetch } from '@/lib/api-client'
import { StatsGrid } from '@/components/dashboard/stats-grid'
import type { DashboardStats } from '@/lib/api/stats'

export default async function DashboardPage() {
  const session = await auth()

  let initialStats: DashboardStats | undefined
  try {
    const res = await apiFetch('/api/v1/stats/dashboard', session!)
    initialStats = await res.json()
  } catch {
    // SSR fails gracefully — client will refetch via TanStack Query
  }

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">Tableau de bord</h1>
      <StatsGrid initialData={initialStats} />
    </div>
  )
}
