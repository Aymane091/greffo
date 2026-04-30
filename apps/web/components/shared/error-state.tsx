import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'

interface Props {
  title?: string
  description?: string
}

export function ErrorState({
  title = 'Erreur',
  description = 'Une erreur est survenue. Veuillez réessayer.',
}: Props) {
  return (
    <Alert variant="destructive">
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription>{description}</AlertDescription>
    </Alert>
  )
}
