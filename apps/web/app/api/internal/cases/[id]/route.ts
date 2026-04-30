import { proxyToApi } from '@/lib/api/internal-proxy'

type Params = { params: Promise<{ id: string }> }

export async function GET(req: Request, { params }: Params) {
  const { id } = await params
  return proxyToApi(req, `/api/v1/cases/${id}`)
}

export async function PATCH(req: Request, { params }: Params) {
  const { id } = await params
  const body = await req.json()
  return proxyToApi(req, `/api/v1/cases/${id}`, { body })
}

export async function DELETE(req: Request, { params }: Params) {
  const { id } = await params
  return proxyToApi(req, `/api/v1/cases/${id}`, { method: 'DELETE' })
}
