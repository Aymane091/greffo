export type CaseItem = {
  id: string
  organization_id: string
  name: string
  reference: string | null
  description: string | null
  created_by: string | null
  archived_at: string | null
  created_at: string
}

export type CasePage = {
  items: CaseItem[]
  total: number
  page: number
  size: number
  pages: number
}

export type CaseCreate = {
  name: string
  reference?: string | undefined
  description?: string | undefined
}

export type CaseUpdate = {
  name?: string | undefined
  reference?: string | undefined
  description?: string | undefined
}

export async function fetchCases(params?: {
  archived?: 'false' | 'true' | 'all'
  page?: number
  query?: string | undefined
}): Promise<CasePage> {
  const q = new URLSearchParams()
  if (params?.archived) q.set('archived', params.archived)
  if (params?.page) q.set('page', String(params.page))
  if (params?.query?.trim()) q.set('query', params.query.trim())
  const qs = q.toString()
  const res = await fetch(`/api/internal/cases${qs ? '?' + qs : ''}`)
  if (!res.ok) throw new Error('Failed to fetch cases')
  return res.json()
}

export async function createCase(data: CaseCreate): Promise<CaseItem> {
  const res = await fetch('/api/internal/cases', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('Failed to create case')
  return res.json()
}

export async function updateCase(id: string, data: CaseUpdate): Promise<CaseItem> {
  const res = await fetch(`/api/internal/cases/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('Failed to update case')
  return res.json()
}

export async function archiveCase(id: string): Promise<CaseItem> {
  const res = await fetch(`/api/internal/cases/${id}/archive`, { method: 'POST' })
  if (!res.ok) throw new Error('Failed to archive case')
  return res.json()
}

export async function unarchiveCase(id: string): Promise<CaseItem> {
  const res = await fetch(`/api/internal/cases/${id}/unarchive`, { method: 'POST' })
  if (!res.ok) throw new Error('Failed to unarchive case')
  return res.json()
}

export async function deleteCase(id: string): Promise<void> {
  const res = await fetch(`/api/internal/cases/${id}`, { method: 'DELETE' })
  if (!res.ok) throw new Error('Failed to delete case')
}
