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
  error_message: string | null
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

export async function createTranscription(data: {
  case_id: string
  title: string
  language: string
}): Promise<TranscriptionItem> {
  const res = await fetch('/api/internal/transcriptions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('Failed to create transcription')
  return res.json()
}

export async function getUploadUrl(
  id: string,
): Promise<{ upload_url: string; expires_at: string }> {
  const res = await fetch(`/api/internal/transcriptions/${id}/upload-url`, {
    method: 'POST',
  })
  if (!res.ok) throw new Error('Failed to get upload URL')
  return res.json()
}

export async function confirmUpload(id: string): Promise<TranscriptionItem> {
  const res = await fetch(`/api/internal/transcriptions/${id}/confirm-upload`, {
    method: 'POST',
  })
  if (!res.ok) throw new Error('Failed to confirm upload')
  return res.json()
}

export async function retryTranscription(id: string): Promise<TranscriptionItem> {
  const res = await fetch(`/api/internal/transcriptions/${id}/retry`, {
    method: 'POST',
  })
  if (!res.ok) throw new Error('Failed to retry transcription')
  return res.json()
}

export async function deleteTranscription(id: string): Promise<void> {
  const res = await fetch(`/api/internal/transcriptions/${id}`, { method: 'DELETE' })
  if (!res.ok) throw new Error('Failed to delete transcription')
}
