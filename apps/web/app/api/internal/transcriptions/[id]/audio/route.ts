import { auth } from '@/lib/auth'
import { serverEnv } from '@/lib/env'
import { NextResponse } from 'next/server'

type Params = { params: Promise<{ id: string }> }

const FORWARDED_RESPONSE_HEADERS = [
  'content-type',
  'content-length',
  'content-range',
  'accept-ranges',
]

export async function GET(req: Request, { params }: Params) {
  const session = await auth()
  if (!session?.userId) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const { id } = await params

  const apiHeaders: Record<string, string> = {
    'X-Org-Id': session.organizationId,
    'X-User-Id': session.userId,
  }
  const range = req.headers.get('range')
  if (range) apiHeaders['Range'] = range

  const apiRes = await fetch(
    `${serverEnv.API_BASE_URL}/api/v1/transcriptions/${id}/audio`,
    { headers: apiHeaders },
  )

  if (!apiRes.ok) {
    return NextResponse.json({ error: 'Not found' }, { status: apiRes.status })
  }

  const responseHeaders: Record<string, string> = {}
  for (const key of FORWARDED_RESPONSE_HEADERS) {
    const val = apiRes.headers.get(key)
    if (val) responseHeaders[key] = val
  }

  return new Response(apiRes.body, {
    status: apiRes.status,
    headers: responseHeaders,
  })
}
