import NextAuth from 'next-auth'
import type { NextAuthConfig } from 'next-auth'
import type { EmailConfig } from 'next-auth/providers/email'
import { pool } from '@/lib/db'
import { serverEnv } from '@/lib/env'
import { makeAdapter } from '@/lib/auth-adapter'
import { sendMagicLink } from '@/lib/resend'

declare module 'next-auth' {
  interface Session {
    userId: string
    organizationId: string
    role: string
  }
}

declare module 'next-auth/jwt' {
  interface JWT {
    userId?: string
    organizationId?: string
    role?: string
  }
}

const adapter = makeAdapter(pool)

const emailProvider: EmailConfig = {
  id: 'email',
  type: 'email',
  name: 'Email',
  from: `${serverEnv.RESEND_FROM_NAME} <${serverEnv.RESEND_FROM_EMAIL}>`,
  maxAge: 24 * 60 * 60,
  sendVerificationRequest: async ({ identifier, url }) => {
    const user = await adapter.getUserByEmail!(identifier)
    if (!user) {
      // Option B: unknown email — silently skip, show neutral UI
      console.info('[auth] magic link skipped for unknown email (audit)')
      return
    }
    await sendMagicLink({ to: identifier, url })
  },
}

export const config: NextAuthConfig = {
  secret: serverEnv.AUTH_SECRET,
  adapter,
  session: { strategy: 'jwt' },
  providers: [emailProvider],
  pages: {
    signIn: '/login',
    verifyRequest: '/auth/verify',
    error: '/login',
  },
  callbacks: {
    async jwt({ token, user }) {
      if (user?.email) {
        const { rows } = await pool.query<{
          id: string
          organization_id: string
          role: string
        }>(
          'SELECT id, organization_id, role FROM users WHERE email = $1 LIMIT 1',
          [user.email],
        )
        const dbUser = rows[0]
        if (dbUser) {
          token.userId = dbUser.id
          token.organizationId = dbUser.organization_id
          token.role = dbUser.role
        }
      }
      return token
    },

    session({ session, token }) {
      session.userId = token.userId ?? ''
      session.organizationId = token.organizationId ?? ''
      session.role = token.role ?? ''
      return session
    },
  },
}

export const { handlers, auth, signIn, signOut } = NextAuth(config)
