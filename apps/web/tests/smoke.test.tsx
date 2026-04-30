import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import VerifyPage from '@/app/(auth)/auth/verify/page'

describe('Auth verify page', () => {
  it('affiche le message de vérification', () => {
    render(<VerifyPage />)
    expect(screen.getByRole('heading', { name: /vérifiez/i })).toBeDefined()
  })
})
