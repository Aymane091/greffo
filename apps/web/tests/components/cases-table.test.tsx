import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { CasesTable } from '@/components/cases/cases-table'
import type { CasePage } from '@/lib/api/cases'

vi.mock('next/link', () => ({
  default: ({
    children,
    href,
  }: {
    children: React.ReactNode
    href: string
  }) => <a href={href}>{children}</a>,
}))

vi.mock('next/navigation', () => ({
  useRouter: vi.fn(() => ({ push: vi.fn() })),
  usePathname: vi.fn(() => '/cases'),
  useSearchParams: vi.fn(() => new URLSearchParams()),
}))

vi.mock('date-fns', () => ({
  formatDistanceToNow: () => 'il y a 2 jours',
}))

vi.mock('date-fns/locale', () => ({ fr: {} }))

vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }))

function wrap(ui: React.ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>)
}

const emptyPage: CasePage = { items: [], total: 0, page: 1, size: 50, pages: 0 }

const samplePage: CasePage = {
  items: [
    {
      id: 'case-1',
      organization_id: 'org-1',
      name: 'Affaire Dupont',
      reference: 'REF-001',
      description: null,
      created_by: null,
      archived_at: null,
      created_at: '2024-01-15T10:00:00Z',
    },
    {
      id: 'case-2',
      organization_id: 'org-1',
      name: 'Dossier Martin',
      reference: null,
      description: null,
      created_by: null,
      archived_at: '2024-02-01T00:00:00Z',
      created_at: '2024-01-20T10:00:00Z',
    },
  ],
  total: 2,
  page: 1,
  size: 50,
  pages: 1,
}

describe('CasesTable', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows empty state for active tab when no cases', () => {
    wrap(<CasesTable initialData={emptyPage} archived="false" />)
    expect(screen.getByText('Aucun dossier')).toBeDefined()
    expect(screen.getByText('Créez votre premier dossier pour commencer.')).toBeDefined()
  })

  it('shows empty state for archived tab', () => {
    wrap(<CasesTable initialData={emptyPage} archived="true" />)
    expect(screen.getByText('Aucun dossier archivé.')).toBeDefined()
  })

  it('shows no-results empty state with query', () => {
    // CasesTable ignores initialData when query is set — pass it explicitly
    // to skip the loading state in tests (no network available)
    const emptyWithQuery: CasePage = { ...emptyPage }
    // We provide initialData via the queryClient cache directly
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    client.setQueryData(['cases', { archived: 'false', query: 'xyz' }], emptyWithQuery)
    const { getByText } = render(
      <QueryClientProvider client={client}>
        <CasesTable archived="false" query="xyz" />
      </QueryClientProvider>,
    )
    expect(getByText(/xyz/)).toBeDefined()
  })

  it('renders case rows with name and reference', () => {
    wrap(<CasesTable initialData={samplePage} />)
    expect(screen.getByText('Affaire Dupont')).toBeDefined()
    expect(screen.getByText('REF-001')).toBeDefined()
    expect(screen.getByText('Dossier Martin')).toBeDefined()
  })

  it('renders links to case detail pages', () => {
    wrap(<CasesTable initialData={samplePage} />)
    const link = screen.getByRole('link', { name: 'Affaire Dupont' })
    expect(link.getAttribute('href')).toBe('/cases/case-1')
  })

  it('shows — when reference is null', () => {
    wrap(<CasesTable initialData={samplePage} />)
    expect(screen.getAllByText('—').length).toBeGreaterThan(0)
  })
})
