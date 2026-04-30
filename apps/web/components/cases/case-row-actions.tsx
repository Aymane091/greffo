'use client'

import { useState } from 'react'
import { useQueryClient, useMutation } from '@tanstack/react-query'
import { MoreHorizontal, Archive, ArchiveRestore, Pencil, Trash2 } from 'lucide-react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Button } from '@/components/ui/button'
import { ConfirmDialog } from '@/components/shared/confirm-dialog'
import { CaseFormDialog } from './case-form-dialog'
import { archiveCase, unarchiveCase, deleteCase, type CaseItem } from '@/lib/api/cases'
import { toast } from 'sonner'

export function CaseRowActions({ caseItem }: { caseItem: CaseItem }) {
  const qc = useQueryClient()
  const [editOpen, setEditOpen] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)

  const archiveMut = useMutation({
    mutationFn: () => archiveCase(caseItem.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cases'] })
      toast.success('Dossier archivé')
    },
    onError: () => toast.error("Erreur lors de l'archivage"),
  })

  const unarchiveMut = useMutation({
    mutationFn: () => unarchiveCase(caseItem.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cases'] })
      toast.success('Dossier désarchivé')
    },
    onError: () => toast.error('Erreur lors du désarchivage'),
  })

  const deleteMut = useMutation({
    mutationFn: () => deleteCase(caseItem.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cases'] })
      toast.success('Dossier supprimé')
    },
    onError: () => toast.error('Erreur lors de la suppression'),
  })

  const isArchived = !!caseItem.archived_at

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
          <DropdownMenuItem onClick={() => setEditOpen(true)}>
            <Pencil className="mr-2 h-4 w-4" />
            Modifier
          </DropdownMenuItem>
          {isArchived ? (
            <DropdownMenuItem
              onClick={() => unarchiveMut.mutate()}
              disabled={unarchiveMut.isPending}
            >
              <ArchiveRestore className="mr-2 h-4 w-4" />
              Désarchiver
            </DropdownMenuItem>
          ) : (
            <DropdownMenuItem
              onClick={() => archiveMut.mutate()}
              disabled={archiveMut.isPending}
            >
              <Archive className="mr-2 h-4 w-4" />
              Archiver
            </DropdownMenuItem>
          )}
          <DropdownMenuSeparator />
          <DropdownMenuItem
            onClick={() => setDeleteOpen(true)}
            className="text-destructive focus:text-destructive"
          >
            <Trash2 className="mr-2 h-4 w-4" />
            Supprimer
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <CaseFormDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        mode="edit"
        initialValues={caseItem}
      />

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
