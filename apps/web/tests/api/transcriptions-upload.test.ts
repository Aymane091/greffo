import { vi, describe, it, expect, beforeEach } from 'vitest'

vi.mock('@/lib/auth', () => ({ auth: vi.fn() }))
vi.mock('@/lib/api-client', () => {
  class ApiError extends Error {
    constructor(public status: number, public body: unknown) { super(`API ${status}`) }
  }
  return { apiFetch: vi.fn(), ApiError }
})

import { POST as postCreate } from '@/app/api/internal/transcriptions/route'
import { POST as postUploadUrl } from '@/app/api/internal/transcriptions/[id]/upload-url/route'
import { POST as postConfirm } from '@/app/api/internal/transcriptions/[id]/confirm-upload/route'
import { POST as postRetry } from '@/app/api/internal/transcriptions/[id]/retry/route'
import { DELETE } from '@/app/api/internal/transcriptions/[id]/route'
import { auth } from '@/lib/auth'
import { apiFetch } from '@/lib/api-client'

const params = (id: string) => ({ params: Promise.resolve({ id }) })

describe('POST /api/internal/transcriptions', () => {
  beforeEach(() => vi.resetAllMocks())

  it('returns 401 when not authenticated', async () => {
    vi.mocked(auth).mockResolvedValue(null as never)
    const req = new Request('http://localhost/api/internal/transcriptions', {
      method: 'POST',
      body: JSON.stringify({ case_id: 'c1', title: 'Test', language: 'fr' }),
    })
    const res = await postCreate(req)
    expect(res.status).toBe(401)
  })

  it('proxies create to FastAPI', async () => {
    vi.mocked(auth).mockResolvedValue({ userId: 'u1', organizationId: 'o1' } as never)
    const newTr = { id: 'tr-1', status: 'draft', title: 'Test' }
    vi.mocked(apiFetch).mockResolvedValue(new Response(JSON.stringify(newTr), { status: 201 }))

    const req = new Request('http://localhost/api/internal/transcriptions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ case_id: 'c1', title: 'Test', language: 'fr' }),
    })
    const res = await postCreate(req)
    expect(res.status).toBe(200)
    const data = await res.json()
    expect(data.id).toBe('tr-1')
  })
})

describe('POST /api/internal/transcriptions/[id]/upload-url', () => {
  beforeEach(() => vi.resetAllMocks())

  it('returns 401 when not authenticated', async () => {
    vi.mocked(auth).mockResolvedValue(null as never)
    const req = new Request('http://localhost/api/internal/transcriptions/tr-1/upload-url', { method: 'POST' })
    const res = await postUploadUrl(req, params('tr-1'))
    expect(res.status).toBe(401)
  })

  it('proxies to FastAPI and returns upload_url', async () => {
    vi.mocked(auth).mockResolvedValue({ userId: 'u1', organizationId: 'o1' } as never)
    const payload = { upload_url: 'http://localhost:8000/api/v1/storage/upload/tok', expires_at: '2026-05-01T00:00:00Z' }
    vi.mocked(apiFetch).mockResolvedValue(new Response(JSON.stringify(payload), { status: 200 }))

    const req = new Request('http://localhost/api/internal/transcriptions/tr-1/upload-url', { method: 'POST' })
    const res = await postUploadUrl(req, params('tr-1'))
    expect(res.status).toBe(200)
    const data = await res.json()
    expect(data.upload_url).toContain('/storage/upload/')

    const call = vi.mocked(apiFetch).mock.calls[0]!
    expect(call[0]).toContain('/api/v1/transcriptions/tr-1/upload-url')
  })
})

describe('POST /api/internal/transcriptions/[id]/confirm-upload', () => {
  beforeEach(() => vi.resetAllMocks())

  it('returns 401 when not authenticated', async () => {
    vi.mocked(auth).mockResolvedValue(null as never)
    const req = new Request('http://localhost/...', { method: 'POST' })
    const res = await postConfirm(req, params('tr-1'))
    expect(res.status).toBe(401)
  })
})

describe('POST /api/internal/transcriptions/[id]/retry', () => {
  beforeEach(() => vi.resetAllMocks())

  it('returns 401 when not authenticated', async () => {
    vi.mocked(auth).mockResolvedValue(null as never)
    const req = new Request('http://localhost/...', { method: 'POST' })
    const res = await postRetry(req, params('tr-1'))
    expect(res.status).toBe(401)
  })
})

describe('DELETE /api/internal/transcriptions/[id]', () => {
  beforeEach(() => vi.resetAllMocks())

  it('returns 401 when not authenticated', async () => {
    vi.mocked(auth).mockResolvedValue(null as never)
    const req = new Request('http://localhost/...', { method: 'DELETE' })
    const res = await DELETE(req, params('tr-1'))
    expect(res.status).toBe(401)
  })
})
