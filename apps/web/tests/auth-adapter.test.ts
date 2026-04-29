/**
 * Integration tests for the auth adapter.
 * Uses a real PostgreSQL connection to greffo_test.
 * Requires greffo_test DB to be up with the migration applied.
 */
import { Pool } from 'pg'
import { afterAll, afterEach, beforeAll, describe, expect, it } from 'vitest'
import { makeAdapter } from '@/lib/auth-adapter'

const TEST_DB_URL =
  process.env['TEST_POSTGRES_URL'] ??
  'postgresql://greffo:greffo_local@localhost:5432/greffo_test'

let pool: Pool

beforeAll(() => {
  pool = new Pool({ connectionString: TEST_DB_URL })
})

afterAll(async () => {
  await pool.end()
})

afterEach(async () => {
  await pool.query("DELETE FROM auth_verification_tokens WHERE identifier LIKE 'test-%'")
  await pool.query("DELETE FROM users WHERE email LIKE 'adapter-test-%'")
})

describe('makeAdapter', () => {
  const adapter = () => makeAdapter(pool)

  it('getUserByEmail — returns null for unknown email', async () => {
    const result = await adapter().getUserByEmail!('nobody@unknown.com')
    expect(result).toBeNull()
  })

  it('getUserByEmail — returns user for existing email', async () => {
    // Insert a test user
    const email = `adapter-test-${Date.now()}@cabinet.fr`
    const orgResult = await pool.query<{ id: string }>(
      `SELECT id FROM organizations LIMIT 1`,
    )
    const orgId = orgResult.rows[0]?.id
    if (!orgId) {
      console.warn('No organization found in test DB — skipping user lookup test')
      return
    }
    const userId = `01TEST${Date.now()}`.padEnd(26, '0').slice(0, 26)
    await pool.query(
      `INSERT INTO users (id, organization_id, email, email_hash, role)
       VALUES ($1, $2, $3, encode(sha256($3::bytea), 'hex'), 'member')`,
      [userId, orgId, email],
    )

    const user = await adapter().getUserByEmail!(email)
    expect(user).not.toBeNull()
    expect(user?.email).toBe(email)
    expect(user?.id).toBe(userId)
  })

  it('createVerificationToken — stores token and useVerificationToken retrieves it', async () => {
    const token = {
      identifier: `test-${Date.now()}@example.com`,
      token: 'abc123token',
      expires: new Date(Date.now() + 60_000),
    }

    await adapter().createVerificationToken!(token)

    const retrieved = await adapter().useVerificationToken!({
      identifier: token.identifier,
      token: token.token,
    })

    expect(retrieved).not.toBeNull()
    expect(retrieved?.identifier).toBe(token.identifier)
    expect(retrieved?.token).toBe(token.token)
  })

  it('useVerificationToken — returns null for non-existent token', async () => {
    const result = await adapter().useVerificationToken!({
      identifier: `test-ghost@example.com`,
      token: 'no-such-token',
    })
    expect(result).toBeNull()
  })

  it('useVerificationToken — is idempotent (DELETE RETURNING, second call returns null)', async () => {
    const token = {
      identifier: `test-idem-${Date.now()}@example.com`,
      token: 'idem-token-xyz',
      expires: new Date(Date.now() + 60_000),
    }
    await adapter().createVerificationToken!(token)

    const first = await adapter().useVerificationToken!({
      identifier: token.identifier,
      token: token.token,
    })
    const second = await adapter().useVerificationToken!({
      identifier: token.identifier,
      token: token.token,
    })

    expect(first).not.toBeNull()
    expect(second).toBeNull()
  })
})
