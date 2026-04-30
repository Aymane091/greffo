import { proxyToApi } from '@/lib/api/internal-proxy'

type Params = { params: Promise<{ id: string }> }

export async function GET(req: Request, { params }: Params) {
  const { id } = await params
  return proxyToApi(req, `/api/v1/transcriptions/${id}`)
}

export async function DELETE(req: Request, { params }: Params) {
  const { id } = await params
  return proxyToApi(req, `/api/v1/transcriptions/${id}`, { method: 'DELETE' })
}
