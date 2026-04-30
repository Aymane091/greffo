import { vi, describe, it, expect, beforeEach } from 'vitest'

vi.mock('@/lib/auth', () => ({
  auth: vi.fn(),
}))

vi.mock('@/lib/api-client', () => {
  class ApiError extends Error {
    constructor(
      public status: number,
      public body: unknown,
    ) {
      super(`API ${status}`)
    }
  }
  return { apiFetch: vi.fn(), ApiError }
})

import { GET } from '@/app/api/internal/transcriptions/[id]/route'
import { auth } from '@/lib/auth'
import { apiFetch } from '@/lib/api-client'

const mockTranscription = {
  id: 'tr-1',
  organization_id: 'org-1',
  case_id: 'case-1',
  user_id: null,
  title: 'Audition principale',
  status: 'done',
  progress_pct: null,
  language: 'fr',
  audio_duration_s: 3600,
  audio_size_bytes: null,
  audio_format: null,
  error_code: null,
  error_message: null,
  created_at: '2024-01-15T10:00:00Z',
  processing_started_at: null,
  processing_ended_at: null,
}

describe('GET /api/internal/transcriptions/[id]', () => {
  beforeEach(() => vi.resetAllMocks())

  it('returns 401 when not authenticated', async () => {
    vi.mocked(auth).mockResolvedValue(null as never)
    const req = new Request('http://localhost/api/internal/transcriptions/tr-1')
    const res = await GET(req, { params: Promise.resolve({ id: 'tr-1' }) })
    expect(res.status).toBe(401)
  })

  it('proxies to FastAPI and returns transcription', async () => {
    vi.mocked(auth).mockResolvedValue({ userId: 'u1', organizationId: 'o1' } as never)
    vi.mocked(apiFetch).mockResolvedValue(
      new Response(JSON.stringify(mockTranscription), { status: 200 }),
    )

    const req = new Request('http://localhost/api/internal/transcriptions/tr-1')
    const res = await GET(req, { params: Promise.resolve({ id: 'tr-1' }) })
    expect(res.status).toBe(200)
    const data = await res.json()
    expect(data.id).toBe('tr-1')
    expect(data.title).toBe('Audition principale')

    const call = vi.mocked(apiFetch).mock.calls[0]!
    expect(call[0]).toContain('/api/v1/transcriptions/tr-1')
  })
})
