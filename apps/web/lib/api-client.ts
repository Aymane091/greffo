import { serverEnv } from '@/lib/env'

type RequestInit = globalThis.RequestInit

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly body: unknown,
  ) {
    super(`API error ${status}`)
  }
}

export async function apiFetch(
  path: string,
  session: { userId: string; organizationId: string },
  init: RequestInit = {},
): Promise<Response> {
  const url = `${serverEnv.API_BASE_URL}${path}`
  const headers = new Headers(init.headers as HeadersInit | undefined)
  headers.set('X-Org-Id', session.organizationId)
  headers.set('X-User-Id', session.userId)
  if (!headers.has('Content-Type') && !(init.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }

  const res = await fetch(url, { ...init, headers })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new ApiError(res.status, body)
  }
  return res
}
