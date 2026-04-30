import { Badge } from '@/components/ui/badge'
import type { TranscriptionItem } from '@/lib/api/transcriptions'

const CONFIG: Record<
  TranscriptionItem['status'],
  { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' }
> = {
  draft: { label: 'Brouillon', variant: 'outline' },
  queued: { label: 'En attente', variant: 'secondary' },
  processing: { label: 'En cours', variant: 'default' },
  done: { label: 'Terminé', variant: 'default' },
  failed: { label: 'Erreur', variant: 'destructive' },
}

export function TranscriptionStatusBadge({
  status,
}: {
  status: TranscriptionItem['status']
}) {
  const { label, variant } = CONFIG[status] ?? { label: status, variant: 'outline' }
  return <Badge variant={variant}>{label}</Badge>
}
