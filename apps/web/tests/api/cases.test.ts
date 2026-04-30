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

import { GET, POST } from '@/app/api/internal/cases/route'
import { auth } from '@/lib/auth'
import { apiFetch } from '@/lib/api-client'

const mockPage = { items: [], total: 0, page: 1, size: 50, pages: 0 }

describe('GET /api/internal/cases', () => {
  beforeEach(() => vi.resetAllMocks())

  it('returns 401 when not authenticated', async () => {
    vi.mocked(auth).mockResolvedValue(null as never)
    const req = new Request('http://localhost/api/internal/cases')
    const res = await GET(req)
    expect(res.status).toBe(401)
  })

  it('proxies to FastAPI and returns cases', async () => {
    vi.mocked(auth).mockResolvedValue({ userId: 'u1', organizationId: 'o1' } as never)
    const mockRes = new Response(JSON.stringify(mockPage), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    })
    vi.mocked(apiFetch).mockResolvedValue(mockRes)

    const req = new Request('http://localhost/api/internal/cases')
    const res = await GET(req)
    expect(res.status).toBe(200)
    const data = await res.json()
    expect(data.items).toEqual([])
    expect(data.total).toBe(0)
  })

  it('forwards query params to FastAPI', async () => {
    vi.mocked(auth).mockResolvedValue({ userId: 'u1', organizationId: 'o1' } as never)
    vi.mocked(apiFetch).mockResolvedValue(
      new Response(JSON.stringify(mockPage), { status: 200 }),
    )

    const req = new Request('http://localhost/api/internal/cases?archived=true&page=2')
    await GET(req)

    const call = vi.mocked(apiFetch).mock.calls[0]!
    expect(call[0]).toContain('archived=true')
    expect(call[0]).toContain('page=2')
  })
})

describe('POST /api/internal/cases', () => {
  beforeEach(() => vi.resetAllMocks())

  it('returns 401 when not authenticated', async () => {
    vi.mocked(auth).mockResolvedValue(null as never)
    const req = new Request('http://localhost/api/internal/cases', {
      method: 'POST',
      body: JSON.stringify({ name: 'Test' }),
    })
    const res = await POST(req)
    expect(res.status).toBe(401)
  })

  it('creates a case and returns 200', async () => {
    vi.mocked(auth).mockResolvedValue({ userId: 'u1', organizationId: 'o1' } as never)
    const newCase = { id: 'c1', name: 'Test', organization_id: 'o1' }
    vi.mocked(apiFetch).mockResolvedValue(
      new Response(JSON.stringify(newCase), { status: 201 }),
    )

    const req = new Request('http://localhost/api/internal/cases', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: 'Test' }),
    })
    const res = await POST(req)
    expect(res.status).toBe(200)
    const data = await res.json()
    expect(data.name).toBe('Test')
  })
})
