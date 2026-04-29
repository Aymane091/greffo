import type { Adapter, AdapterUser, VerificationToken } from 'next-auth/adapters'
import type { Pool } from 'pg'

export interface DbUser {
  id: string
  organization_id: string
  email: string
  role: string
}

export function makeAdapter(pool: Pool): Adapter {
  return {
    async getUserByEmail(email: string): Promise<AdapterUser | null> {
      const { rows } = await pool.query<DbUser>(
        'SELECT id, organization_id, email, role FROM users WHERE email = $1 LIMIT 1',
        [email],
      )
      const row = rows[0]
      if (!row) return null
      return { id: row.id, email: row.email, emailVerified: null }
    },

    async updateUser(
      user: Partial<AdapterUser> & Pick<AdapterUser, 'id'>,
    ): Promise<AdapterUser> {
      // We don't persist emailVerified — users are managed out-of-band.
      const { rows } = await pool.query<DbUser>(
        'SELECT id, organization_id, email, role FROM users WHERE id = $1 LIMIT 1',
        [user.id],
      )
      const row = rows[0]
      if (!row) return { id: user.id, email: user.email ?? '', emailVerified: null }
      return { id: row.id, email: row.email, emailVerified: null }
    },

    async createUser(_user: AdapterUser): Promise<AdapterUser> {
      // Option B: only reached if an unknown email somehow passed verification.
      // We return a dummy so Auth.js can complete the flow; the JWT callback
      // will see missing org/role and the session will lack those fields.
      return { ..._user, emailVerified: null }
    },

    async createVerificationToken(token: VerificationToken): Promise<VerificationToken> {
      await pool.query(
        `INSERT INTO auth_verification_tokens (identifier, token, expires)
         VALUES ($1, $2, $3)
         ON CONFLICT (identifier, token) DO UPDATE SET expires = EXCLUDED.expires`,
        [token.identifier, token.token, token.expires],
      )
      return token
    },

    async useVerificationToken({
      identifier,
      token,
    }: {
      identifier: string
      token: string
    }): Promise<VerificationToken | null> {
      const { rows } = await pool.query<{ identifier: string; token: string; expires: Date }>(
        `DELETE FROM auth_verification_tokens
         WHERE identifier = $1 AND token = $2
         RETURNING identifier, token, expires`,
        [identifier, token],
      )
      const row = rows[0]
      if (!row) return null
      return { identifier: row.identifier, token: row.token, expires: row.expires }
    },
  }
}
