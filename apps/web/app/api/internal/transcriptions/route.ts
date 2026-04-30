import { proxyToApi } from '@/lib/api/internal-proxy'

export async function POST(req: Request) {
  const body = await req.json()
  return proxyToApi(req, '/api/v1/transcriptions', { method: 'POST', body })
}
