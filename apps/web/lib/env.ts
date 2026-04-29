import { z } from 'zod'

const clientSchema = z.object({
  NEXT_PUBLIC_APP_URL: z.string().url().optional(),
  NEXT_PUBLIC_API_URL: z.string().url().optional(),
})

const serverSchema = z.object({
  NODE_ENV: z.enum(['development', 'production', 'test']).default('development'),
  AUTH_SECRET: z.string().min(1),
  RESEND_API_KEY: z.string().min(1),
  RESEND_FROM_EMAIL: z.string().email().default('connexion@greffo.fr'),
  RESEND_FROM_NAME: z.string().default('Greffo'),
  POSTGRES_URL: z.string().min(1),
  API_BASE_URL: z.string().url().default('http://localhost:8000'),
})

export const clientEnv = clientSchema.parse({
  NEXT_PUBLIC_APP_URL: process.env.NEXT_PUBLIC_APP_URL,
  NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
})

// Only evaluated server-side — throws at startup if required vars are missing
export const serverEnv = serverSchema.parse({
  NODE_ENV: process.env.NODE_ENV,
  AUTH_SECRET: process.env.AUTH_SECRET,
  RESEND_API_KEY: process.env.RESEND_API_KEY,
  RESEND_FROM_EMAIL: process.env.RESEND_FROM_EMAIL,
  RESEND_FROM_NAME: process.env.RESEND_FROM_NAME,
  POSTGRES_URL: process.env.POSTGRES_URL,
  API_BASE_URL: process.env.API_BASE_URL,
})
