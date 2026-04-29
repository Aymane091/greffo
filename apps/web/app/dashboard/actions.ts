'use server'

import { auth, signOut } from '@/lib/auth'
import { apiFetch, ApiError } from '@/lib/api-client'

export async function signOutAction() {
  await signOut({ redirectTo: '/login' })
}

export type TestApiResult =
  | { ok: true; data: unknown }
  | { ok: false; status: number; error: string }

export async function testApiAction(): Promise<TestApiResult> {
  const session = await auth()
  if (!session?.userId || !session?.organizationId) {
    return { ok: false, status: 401, error: 'Session invalide ou expirée' }
  }

  try {
    const res = await apiFetch('/api/v1/cases?page=1&page_size=5', {
      userId: session.userId,
      organizationId: session.organizationId,
    })
    const data = (await res.json()) as unknown
    return { ok: true, data }
  } catch (err) {
    if (err instanceof ApiError) {
      return {
        ok: false,
        status: err.status,
        error: `HTTP ${err.status}: ${JSON.stringify(err.body)}`,
      }
    }
    return { ok: false, status: 0, error: (err as Error).message }
  }
}
