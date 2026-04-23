import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import Home from '@/app/page'

describe('Home page', () => {
  it('affiche le nom du produit', () => {
    render(<Home />)
    expect(screen.getByRole('heading', { name: /greffo/i })).toBeDefined()
  })
})
