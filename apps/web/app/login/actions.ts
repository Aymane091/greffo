'use server'

import { signIn } from '@/lib/auth'

export async function loginAction(formData: FormData) {
  const email = formData.get('email')?.toString().trim()
  if (!email) return
  await signIn('email', { email, redirectTo: '/dashboard' })
}
