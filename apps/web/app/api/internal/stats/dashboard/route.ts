import { proxyToApi } from '@/lib/api/internal-proxy'

export async function GET(req: Request) {
  return proxyToApi(req, '/api/v1/stats/dashboard')
}
