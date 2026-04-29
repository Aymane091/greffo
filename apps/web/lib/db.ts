import { Pool } from 'pg'
import { serverEnv } from '@/lib/env'

export const pool = new Pool({ connectionString: serverEnv.POSTGRES_URL })
