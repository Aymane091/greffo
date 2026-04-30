'use client'

import { useState } from 'react'
import { useQueryClient, useMutation } from '@tanstack/react-query'
import { MoreHorizontal, Archive, Trash2 } from 'lucide-react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Button } from '@/components/ui/button'
import { ConfirmDialog } from '@/components/shared/confirm-dialog'
import { archiveCase, deleteCase, type CaseItem } from '@/lib/api/cases'
import { toast } from 'sonner'

export function CaseRowActions({ caseItem }: { caseItem: CaseItem }) {
  const qc = useQueryClient()
  const [deleteOpen, setDeleteOpen] = useState(false)

  const archiveMut = useMutation({
    mutationFn: () => archiveCase(caseItem.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cases'] })
      toast.success('Dossier archivé')
    },
    onError: () => toast.error("Erreur lors de l'archivage"),
  })

  const deleteMut = useMutation({
    mutationFn: () => deleteCase(caseItem.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cases'] })
      toast.success('Dossier supprimé')
    },
    onError: () => toast.error('Erreur lors de la suppression'),
  })

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon" className="h-8 w-8">
            <MoreHorizontal className="h-4 w-4" />
            <span className="sr-only">Actions</span>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          {!caseItem.archived_at && (
            <DropdownMenuItem
              onClick={() => archiveMut.mutate()}
              disabled={archiveMut.isPending}
            >
              <Archive className="mr-2 h-4 w-4" />
              Archiver
            </DropdownMenuItem>
          )}
          <DropdownMenuItem
            onClick={() => setDeleteOpen(true)}
            className="text-destructive focus:text-destructive"
          >
            <Trash2 className="mr-2 h-4 w-4" />
            Supprimer
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Supprimer le dossier ?"
        description="Cette action est irréversible. Le dossier et toutes ses transcriptions seront supprimés."
        onConfirm={() => {
          deleteMut.mutate()
          setDeleteOpen(false)
        }}
      />
    </>
  )
}
