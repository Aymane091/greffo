import { vi, describe, it, expect } from 'vitest'

vi.mock('@/lib/env', () => ({
  serverEnv: {
    AUTH_SECRET: 'test-secret-32-chars-minimum-len',
    RESEND_API_KEY: 'test-key',
    RESEND_FROM_EMAIL: 'test@greffo.fr',
    RESEND_FROM_NAME: 'Greffo',
    POSTGRES_URL: 'postgresql://greffo:greffo_local@localhost:5432/greffo_test',
    NODE_ENV: 'test',
    API_BASE_URL: 'http://localhost:8000',
  },
  clientEnv: {},
}))

vi.mock('@/lib/db', () => ({
  pool: { query: vi.fn() },
}))

vi.mock('@/lib/resend', () => ({
  sendMagicLink: vi.fn(),
}))

// next-auth imports next/server without .js extension — fails in vitest's resolver.
// We only need the config object (plain export), so stub the NextAuth() call.
vi.mock('next-auth', () => ({
  default: vi.fn(() => ({ handlers: {}, auth: vi.fn(), signIn: vi.fn(), signOut: vi.fn() })),
}))

import { config } from '@/lib/auth'

describe('auth config', () => {
  it('pages.verifyRequest pointe vers /auth/verify', () => {
    expect(config.pages?.verifyRequest).toBe('/auth/verify')
  })

  it('pages.signIn pointe vers /login', () => {
    expect(config.pages?.signIn).toBe('/login')
  })

  it('pages.error pointe vers /login', () => {
    expect(config.pages?.error).toBe('/login')
  })

  it('session strategy est jwt', () => {
    expect(config.session?.strategy).toBe('jwt')
  })
})
