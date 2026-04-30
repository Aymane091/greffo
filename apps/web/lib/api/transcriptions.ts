export type TranscriptionItem = {
  id: string
  organization_id: string
  case_id: string | null
  user_id: string | null
  title: string | null
  status: 'draft' | 'queued' | 'processing' | 'done' | 'failed'
  progress_pct: number | null
  language: string
  audio_duration_s: number | null
  audio_size_bytes: number | null
  audio_format: string | null
  error_code: string | null
  created_at: string
  processing_started_at: string | null
  processing_ended_at: string | null
}

export type TranscriptionPage = {
  items: TranscriptionItem[]
  total: number
  page: number
  size: number
  pages: number
}

export async function fetchCaseTranscriptions(
  caseId: string,
): Promise<TranscriptionPage> {
  const res = await fetch(`/api/internal/cases/${caseId}/transcriptions`)
  if (!res.ok) throw new Error('Failed to fetch transcriptions')
  return res.json()
}
