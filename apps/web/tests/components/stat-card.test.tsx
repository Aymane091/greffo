import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { StatCard, StatCardSkeleton } from '@/components/dashboard/stat-card'

describe('StatCard', () => {
  it('renders title and numeric value', () => {
    render(<StatCard title="Dossiers actifs" value={42} />)
    expect(screen.getByText('Dossiers actifs')).toBeDefined()
    expect(screen.getByText('42')).toBeDefined()
  })

  it('renders string value', () => {
    render(<StatCard title="Durée" value="2h 30min" />)
    expect(screen.getByText('2h 30min')).toBeDefined()
  })

  it('renders description when provided', () => {
    render(<StatCard title="Durée" value="1h" description="ce mois" />)
    expect(screen.getByText('ce mois')).toBeDefined()
  })

  it('does not render description when omitted', () => {
    render(<StatCard title="T" value={0} />)
    expect(screen.queryByRole('paragraph')).toBeNull()
  })

  it('renders skeleton without crashing', () => {
    const { container } = render(<StatCardSkeleton />)
    expect(container.firstChild).toBeDefined()
  })
})
