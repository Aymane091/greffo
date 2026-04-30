import { auth } from '@/lib/auth'
import { apiFetch, ApiError } from '@/lib/api-client'
import { NextResponse } from 'next/server'

export async function proxyToApi(
  req: Request,
  apiPath: string,
  options: { method?: string; body?: unknown } = {},
): Promise<NextResponse> {
  const session = await auth()
  if (!session?.userId) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const url = new URL(req.url)
  const pathWithQuery = apiPath + (url.search || '')

  try {
    const init: RequestInit = { method: options.method ?? req.method }
    if (options.body !== undefined) {
      init.body = JSON.stringify(options.body)
    }

    const res = await apiFetch(
      pathWithQuery,
      { userId: session.userId, organizationId: session.organizationId },
      init,
    )

    if (res.status === 204) return new NextResponse(null, { status: 204 })
    return NextResponse.json(await res.json())
  } catch (err) {
    if (err instanceof ApiError) {
      return NextResponse.json(err.body, { status: err.status })
    }
    return NextResponse.json({ error: 'Internal error' }, { status: 500 })
  }
}
