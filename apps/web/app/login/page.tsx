'use server'

import { signIn } from '@/lib/auth'

async function requestMagicLink(formData: FormData) {
  'use server'
  const email = formData.get('email')?.toString().trim()
  if (!email) return

  // signIn with email provider redirects to /auth/verify automatically.
  // For unknown emails, sendVerificationRequest returns silently — same UX.
  await signIn('email', { email, redirectTo: '/auth/verify' })
}

export default function LoginPage() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-8 px-4 py-32">
      <div className="w-full max-w-sm space-y-6">
        <div className="space-y-2 text-center">
          <h1 className="text-3xl font-bold tracking-tight">Connexion</h1>
          <p className="text-muted-foreground">
            Entrez votre adresse e-mail pour recevoir un lien de connexion.
          </p>
        </div>

        <form action={requestMagicLink} className="space-y-4">
          <div className="space-y-2">
            <label htmlFor="email" className="text-sm font-medium">
              Adresse e-mail
            </label>
            <input
              id="email"
              name="email"
              type="email"
              required
              autoComplete="email"
              placeholder="vous@cabinet.fr"
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>
          <button
            type="submit"
            className="w-full rounded-md bg-foreground px-4 py-2 text-sm font-semibold text-background hover:opacity-90 transition-opacity"
          >
            Envoyer le lien de connexion
          </button>
        </form>
      </div>
    </main>
  )
}
