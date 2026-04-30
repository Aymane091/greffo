'use client'

import { useEffect, useState } from 'react'
import { useQueryClient, useMutation } from '@tanstack/react-query'
import { z } from 'zod'
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
import { Textarea } from '@/components/ui/textarea'
import { createCase, updateCase, type CaseItem } from '@/lib/api/cases'
import { toast } from 'sonner'

const schema = z.object({
  name: z
    .string()
    .trim()
    .min(3, 'Le nom doit contenir au moins 3 caractères')
    .max(200, '200 caractères maximum'),
  reference: z.string().trim().max(100, '100 caractères maximum').optional(),
  description: z
    .string()
    .trim()
    .max(500, '500 caractères maximum')
    .optional(),
})

type FormErrors = Partial<Record<keyof z.infer<typeof schema>, string>>

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  mode?: 'create' | 'edit'
  initialValues?: CaseItem | undefined
}

export function CaseFormDialog({
  open,
  onOpenChange,
  mode = 'create',
  initialValues,
}: Props) {
  const [name, setName] = useState('')
  const [reference, setReference] = useState('')
  const [description, setDescription] = useState('')
  const [errors, setErrors] = useState<FormErrors>({})
  const qc = useQueryClient()

  useEffect(() => {
    if (open) {
      setName(initialValues?.name ?? '')
      setReference(initialValues?.reference ?? '')
      setDescription(initialValues?.description ?? '')
      setErrors({})
    }
  }, [open, initialValues])

  const createMut = useMutation({
    mutationFn: () =>
      createCase({
        name: name.trim(),
        reference: reference.trim() || undefined,
        description: description.trim() || undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cases'] })
      toast.success('Dossier créé')
      onOpenChange(false)
    },
    onError: () => toast.error('Erreur lors de la création'),
  })

  const updateMut = useMutation({
    mutationFn: () =>
      updateCase(initialValues!.id, {
        name: name.trim(),
        reference: reference.trim() || undefined,
        description: description.trim() || undefined,
      }),
    onSuccess: (updated) => {
      qc.invalidateQueries({ queryKey: ['cases'] })
      qc.invalidateQueries({ queryKey: ['case', updated.id] })
      toast.success('Dossier modifié')
      onOpenChange(false)
    },
    onError: () => toast.error('Erreur lors de la modification'),
  })

  const isPending = createMut.isPending || updateMut.isPending

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const result = schema.safeParse({ name, reference: reference || undefined, description: description || undefined })
    if (!result.success) {
      const fieldErrors: FormErrors = {}
      for (const issue of result.error.issues) {
        const key = issue.path[0] as keyof FormErrors
        if (key) fieldErrors[key] = issue.message
      }
      setErrors(fieldErrors)
      return
    }
    setErrors({})
    if (mode === 'edit') {
      updateMut.mutate()
    } else {
      createMut.mutate()
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{mode === 'edit' ? 'Modifier le dossier' : 'Nouveau dossier'}</DialogTitle>
        </DialogHeader>
        <form id="case-form" onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="case-name">Nom *</Label>
            <Input
              id="case-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Ex : Affaire Durand"
              autoFocus
            />
            {errors.name && (
              <p className="text-xs text-destructive">{errors.name}</p>
            )}
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="case-ref">Référence</Label>
            <Input
              id="case-ref"
              value={reference}
              onChange={(e) => setReference(e.target.value)}
              placeholder="Ex : 2024-001"
            />
            {errors.reference && (
              <p className="text-xs text-destructive">{errors.reference}</p>
            )}
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="case-desc">Description</Label>
            <Textarea
              id="case-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Notes sur ce dossier..."
              rows={3}
            />
            {errors.description && (
              <p className="text-xs text-destructive">{errors.description}</p>
            )}
            <p className="text-xs text-muted-foreground text-right">
              {description.length}/500
            </p>
          </div>
        </form>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Annuler
          </Button>
          <Button type="submit" form="case-form" disabled={isPending}>
            {isPending
              ? mode === 'edit'
                ? 'Enregistrement…'
                : 'Création…'
              : mode === 'edit'
                ? 'Enregistrer'
                : 'Créer'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
