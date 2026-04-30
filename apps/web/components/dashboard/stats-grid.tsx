'use client'

import { useQuery } from '@tanstack/react-query'
import { fetchDashboardStats, type DashboardStats } from '@/lib/api/stats'
import { StatCard, StatCardSkeleton } from './stat-card'
import { formatDuration } from '@/lib/format'

interface Props {
  initialData?: DashboardStats | undefined
}

export function StatsGrid({ initialData }: Props) {
  const { data, isLoading } = useQuery({
    queryKey: ['stats', 'dashboard'],
    queryFn: fetchDashboardStats,
    initialData,
    staleTime: 30_000,
  })

  if (isLoading && !data) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <StatCardSkeleton key={i} />
        ))}
      </div>
    )
  }

  if (!data) return null

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <StatCard title="Dossiers actifs" value={data.active_cases} />
      <StatCard title="Dossiers archivés" value={data.archived_cases} />
      <StatCard title="Transcriptions ce mois" value={data.transcriptions_this_month} />
      <StatCard
        title="Durée audio totale"
        value={formatDuration(data.total_audio_duration_seconds)}
        description="dossiers traités ce mois"
      />
    </div>
  )
}
