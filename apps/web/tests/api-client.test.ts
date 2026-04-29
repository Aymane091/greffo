import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'

// Mock env before any imports that depend on it
vi.mock('@/lib/env', () => ({
  serverEnv: {
    API_BASE_URL: 'http://localhost:8000',
    AUTH_SECRET: 'test-secret',
    RESEND_API_KEY: 'test-key',
    RESEND_FROM_EMAIL: 'test@greffo.fr',
    RESEND_FROM_NAME: 'Greffo Test',
    POSTGRES_URL: 'postgresql://greffo:greffo_local@localhost:5432/greffo_test',
    NODE_ENV: 'test',
  },
  clientEnv: {},
}))

import { ApiError, apiFetch } from '@/lib/api-client'

const TEST_SESSION = {
  userId: 'user-001',
  organizationId: 'org-001',
}

describe('apiFetch', () => {
  const fetchSpy = vi.spyOn(globalThis, 'fetch')

  beforeAll(() => {
    fetchSpy.mockReturnValue(new Response('{}', { status: 200 }) as never)
  })

  beforeEach(() => {
    fetchSpy.mockReset()
  })

  it('injects X-Org-Id and X-User-Id headers', async () => {
    fetchSpy.mockResolvedValueOnce(
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    )

    await apiFetch('/api/v1/cases', TEST_SESSION)

    const [url, init] = fetchSpy.mock.calls[0]!
    expect(url).toBe('http://localhost:8000/api/v1/cases')

    const headers = init?.headers as Headers
    expect(headers.get('X-Org-Id')).toBe('org-001')
    expect(headers.get('X-User-Id')).toBe('user-001')
  })

  it('sets Content-Type: application/json by default', async () => {
    fetchSpy.mockResolvedValueOnce(new Response('{}', { status: 200 }))

    await apiFetch('/api/v1/transcriptions', TEST_SESSION, { method: 'POST', body: '{}' })

    const [, init] = fetchSpy.mock.calls[0]!
    const headers = init?.headers as Headers
    expect(headers.get('Content-Type')).toBe('application/json')
  })

  it('does not override existing headers', async () => {
    fetchSpy.mockResolvedValueOnce(new Response('{}', { status: 200 }))

    await apiFetch('/api/v1/cases', TEST_SESSION, {
      headers: { 'X-Custom': 'value' },
    })

    const [, init] = fetchSpy.mock.calls[0]!
    const headers = init?.headers as Headers
    expect(headers.get('X-Custom')).toBe('value')
    expect(headers.get('X-Org-Id')).toBe('org-001')
  })

  it('throws ApiError on non-ok response', async () => {
    fetchSpy.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'Not Found' }), { status: 404 }),
    )

    let caught: unknown
    try {
      await apiFetch('/api/v1/missing', TEST_SESSION)
    } catch (err) {
      caught = err
    }
    expect(caught).toBeInstanceOf(ApiError)
    expect((caught as ApiError).status).toBe(404)
  })

  it('returns Response on success', async () => {
    fetchSpy.mockResolvedValueOnce(new Response(JSON.stringify([]), { status: 200 }))

    const res = await apiFetch('/api/v1/cases', TEST_SESSION)
    expect(res.status).toBe(200)
    expect(await res.json()).toEqual([])
  })
})
