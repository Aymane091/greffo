import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'

vi.mock('next/navigation', () => ({
  notFound: vi.fn(() => { throw new Error('NEXT_NOT_FOUND') }),
  useRouter: vi.fn(() => ({ push: vi.fn() })),
  usePathname: vi.fn(() => '/transcriptions/tr-1'),
  useSearchParams: vi.fn(() => new URLSearchParams()),
}))

vi.mock('next/link', () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}))

vi.mock('@/lib/auth', () => ({
  auth: vi.fn(),
}))

vi.mock('@/lib/api-client', () => {
  class ApiError extends Error {
    constructor(
      public status: number,
      public body: unknown,
    ) {
      super(`API ${status}`)
    }
  }
  return { apiFetch: vi.fn(), ApiError }
})

vi.mock('date-fns', () => ({ formatDistanceToNow: () => 'il y a 2 jours' }))
vi.mock('date-fns/locale', () => ({ fr: {} }))

import TranscriptionDetailPage from '@/app/(app)/transcriptions/[id]/page'
import { auth } from '@/lib/auth'
import { apiFetch } from '@/lib/api-client'

const mockSession = { userId: 'u1', organizationId: 'o1', user: { email: 'test@test.com' } }

const mockTranscription = {
  id: 'tr-1',
  organization_id: 'org-1',
  case_id: 'case-1',
  user_id: null,
  title: 'Audition principale 27/04/2026',
  status: 'done',
  progress_pct: null,
  language: 'fr',
  audio_duration_s: 3661,
  audio_size_bytes: null,
  audio_format: null,
  error_code: null,
  error_message: null,
  created_at: '2024-01-15T10:00:00Z',
  processing_started_at: null,
  processing_ended_at: null,
}

const mockCase = {
  id: 'case-1',
  organization_id: 'org-1',
  name: 'Affaire Dupont',
  reference: 'REF-001',
  description: null,
  created_by: null,
  archived_at: null,
  created_at: '2024-01-01T00:00:00Z',
}

describe('TranscriptionDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(auth).mockResolvedValue(mockSession as never)
  })

  it('calls notFound when transcription is 404', async () => {
    const { ApiError } = await import('@/lib/api-client')
    vi.mocked(apiFetch).mockRejectedValue(new ApiError(404, { detail: 'Not found' }))

    await expect(
      TranscriptionDetailPage({ params: Promise.resolve({ id: 'missing' }) }),
    ).rejects.toThrow('NEXT_NOT_FOUND')
  })

  it('renders title, status badge, case breadcrumb and metadata', async () => {
    vi.mocked(apiFetch)
      .mockResolvedValueOnce(new Response(JSON.stringify(mockTranscription), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(mockCase), { status: 200 }))

    const jsx = await TranscriptionDetailPage({ params: Promise.resolve({ id: 'tr-1' }) })
    render(jsx)

    expect(screen.getByRole('heading', { name: 'Audition principale 27/04/2026' })).toBeDefined()
    expect(screen.getByText('Terminé')).toBeDefined()
    expect(screen.getByText('Affaire Dupont')).toBeDefined()
    expect(screen.getByText('1h 1min')).toBeDefined()
    expect(screen.getByText('fr')).toBeDefined()
    expect(screen.getByText(/Ticket 13b/)).toBeDefined()
  })

  it('renders — for missing duration and breadcrumb fallback when no case', async () => {
    const noCase = { ...mockTranscription, case_id: null, audio_duration_s: null }
    vi.mocked(apiFetch).mockResolvedValueOnce(
      new Response(JSON.stringify(noCase), { status: 200 }),
    )

    const jsx = await TranscriptionDetailPage({ params: Promise.resolve({ id: 'tr-1' }) })
    render(jsx)

    expect(screen.getAllByText('—').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('Dossier')).toBeDefined()
  })
})
