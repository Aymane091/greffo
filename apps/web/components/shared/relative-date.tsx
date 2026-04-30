'use client'

import { formatDistanceToNow } from 'date-fns'
import { fr } from 'date-fns/locale'

export function RelativeDate({ date }: { date: string }) {
  return (
    <time dateTime={date} title={new Date(date).toLocaleDateString('fr-FR')}>
      {formatDistanceToNow(new Date(date), { addSuffix: true, locale: fr })}
    </time>
  )
}
