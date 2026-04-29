import { redirect } from 'next/navigation'
import { auth, signOut } from '@/lib/auth'

async function handleSignOut() {
  'use server'
  await signOut({ redirectTo: '/login' })
}

export default async function DashboardPage() {
  const session = await auth()
  if (!session) redirect('/login')

  return (
    <main className="flex flex-1 flex-col gap-8 px-8 py-12">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Tableau de bord</h1>
        <form action={handleSignOut}>
          <button
            type="submit"
            className="rounded-md border border-border px-4 py-2 text-sm hover:bg-muted transition-colors"
          >
            Se déconnecter
          </button>
        </form>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <InfoCard label="E-mail" value={session.user?.email ?? '—'} />
        <InfoCard label="Organisation" value={session.organizationId || '—'} />
        <InfoCard label="Rôle" value={session.role || '—'} />
      </div>
    </main>
  )
}

function InfoCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-card p-4 space-y-1">
      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{label}</p>
      <p className="text-sm font-semibold truncate">{value}</p>
    </div>
  )
}
