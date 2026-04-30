export type DashboardStats = {
  active_cases: number
  archived_cases: number
  transcriptions_this_month: number
  total_audio_duration_seconds: number
  status_breakdown: {
    done: number
    processing: number
    failed: number
    queued: number
  }
}

export async function fetchDashboardStats(): Promise<DashboardStats> {
  const res = await fetch('/api/internal/stats/dashboard')
  if (!res.ok) throw new Error('Failed to fetch stats')
  return res.json()
}
