'use client'

import { useState } from 'react'
import { useQueryClient, useMutation } from '@tanstack/react-query'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { createCase } from '@/lib/api/cases'
import { toast } from 'sonner'

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function CaseFormDialog({ open, onOpenChange }: Props) {
  const [name, setName] = useState('')
  const [reference, setReference] = useState('')
  const qc = useQueryClient()

  const mut = useMutation({
    mutationFn: () => createCase({ name: name.trim(), reference: reference.trim() || undefined }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cases'] })
      toast.success('Dossier créé')
      setName('')
      setReference('')
      onOpenChange(false)
    },
    onError: () => toast.error('Erreur lors de la création'),
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (name.trim().length < 2) return
    mut.mutate()
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Nouveau dossier</DialogTitle>
        </DialogHeader>
        <form id="case-form" onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="case-name">Nom *</Label>
            <Input
              id="case-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Ex : Affaire Durand"
              required
              minLength={2}
              autoFocus
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="case-ref">Référence</Label>
            <Input
              id="case-ref"
              value={reference}
              onChange={(e) => setReference(e.target.value)}
              placeholder="Ex : 2024-001"
            />
          </div>
        </form>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Annuler
          </Button>
          <Button type="submit" form="case-form" disabled={mut.isPending}>
            {mut.isPending ? 'Création…' : 'Créer'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
