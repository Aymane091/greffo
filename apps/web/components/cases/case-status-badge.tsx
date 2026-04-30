import { Badge } from '@/components/ui/badge'

export function CaseStatusBadge({ archivedAt }: { archivedAt: string | null }) {
  if (archivedAt) {
    return <Badge variant="secondary">Archivé</Badge>
  }
  return <Badge>Actif</Badge>
}
