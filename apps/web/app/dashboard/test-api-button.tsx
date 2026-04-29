'use client'

import { useState, useTransition } from 'react'
import { testApiAction, type TestApiResult } from './actions'

export function TestApiButton() {
  const [result, setResult] = useState<TestApiResult | null>(null)
  const [isPending, startTransition] = useTransition()

  function handleClick() {
    startTransition(async () => {
      const res = await testApiAction()
      setResult(res)
    })
  }

  return (
    <div className="space-y-3">
      <button
        onClick={handleClick}
        disabled={isPending}
        className="rounded-md border border-border px-4 py-2 text-sm font-medium hover:bg-muted transition-colors disabled:opacity-50"
      >
        {isPending ? 'Appel en cours…' : 'Tester l\'API (GET /cases)'}
      </button>

      {result && (
        <pre className="max-h-64 overflow-auto rounded-md bg-muted p-4 text-xs leading-relaxed">
          {result.ok
            ? JSON.stringify(result.data, null, 2)
            : `Erreur ${result.status}: ${result.error}`}
        </pre>
      )}
    </div>
  )
}
