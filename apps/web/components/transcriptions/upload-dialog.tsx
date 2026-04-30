'use client'

import { useCallback, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Upload, X, FileAudio } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { createTranscription, getUploadUrl, confirmUpload } from '@/lib/api/transcriptions'
import { getAudioDuration } from '@/lib/utils/audio-duration'
import { formatDuration, formatFileSize } from '@/lib/format'

const ALLOWED_EXTENSIONS = ['.mp3', '.wav', '.m4a', '.ogg', '.flac', '.opus', '.mp4']
const ALLOWED_MIMES = new Set([
  'audio/mpeg', 'audio/mp4', 'audio/wav', 'audio/ogg',
  'audio/flac', 'audio/x-m4a', 'audio/opus', 'audio/x-wav',
])
const MAX_SIZE_BYTES = 500 * 1024 * 1024

type UploadPhase = 'idle' | 'creating' | 'preparing' | 'uploading' | 'confirming'

const PHASE_LABELS: Record<UploadPhase, string> = {
  idle: '',
  creating: 'Création...',
  preparing: 'Préparation upload...',
  uploading: 'Téléchargement...',
  confirming: 'Lancement transcription...',
}

function validateFile(file: File): string | null {
  const ext = '.' + (file.name.split('.').pop() ?? '').toLowerCase()
  if (!ALLOWED_EXTENSIONS.includes(ext) && !ALLOWED_MIMES.has(file.type)) {
    return `Format non supporté. Formats acceptés : ${ALLOWED_EXTENSIONS.join(', ')}`
  }
  if (file.size > MAX_SIZE_BYTES) {
    return 'Fichier trop volumineux (max 500 Mo)'
  }
  return null
}

async function uploadWithProgress(
  url: string,
  file: File,
  onProgress: (pct: number) => void,
): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('PUT', url)
    xhr.setRequestHeader('Content-Type', file.type || 'application/octet-stream')

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        const pct = Math.round(10 + (e.loaded / e.total) * 80)
        onProgress(pct)
      }
    }

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) resolve()
      else reject(new Error(`Erreur upload (${xhr.status})`))
    }

    xhr.onerror = () => reject(new Error('Erreur réseau lors de l\'upload'))
    xhr.ontimeout = () => reject(new Error('Upload interrompu (timeout)'))
    xhr.send(file)
  })
}

interface Props {
  caseId: string
  onSuccess: () => void
}

export function UploadDialog({ caseId, onSuccess }: Props) {
  const router = useRouter()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [open, setOpen] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const [duration, setDuration] = useState<number | null>(null)
  const [name, setName] = useState('')
  const [language, setLanguage] = useState('fr')
  const [nameError, setNameError] = useState<string | null>(null)
  const [phase, setPhase] = useState<UploadPhase>('idle')
  const [progress, setProgress] = useState(0)
  const [isDragging, setIsDragging] = useState(false)

  const isUploading = phase !== 'idle'
  const canSubmit = !!file && name.trim().length >= 3 && !isUploading

  function reset() {
    setFile(null)
    setDuration(null)
    setName('')
    setLanguage('fr')
    setNameError(null)
    setPhase('idle')
    setProgress(0)
    setIsDragging(false)
  }

  function handleClose(nextOpen: boolean) {
    if (isUploading) return
    if (!nextOpen) reset()
    setOpen(nextOpen)
  }

  function selectFile(selected: File) {
    const err = validateFile(selected)
    if (err) {
      toast.error(err)
      return
    }
    setFile(selected)
    const stem = selected.name.replace(/\.[^.]+$/, '')
    setName(stem)
    setDuration(null)
    getAudioDuration(selected).then(setDuration)
  }

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setIsDragging(false)
      const dropped = e.dataTransfer.files[0]
      if (dropped) selectFile(dropped)
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  )

  async function handleSubmit() {
    if (!file) return
    const trimmed = name.trim()
    if (trimmed.length < 3) {
      setNameError('Le nom doit contenir au moins 3 caractères')
      return
    }
    if (trimmed.length > 200) {
      setNameError('200 caractères maximum')
      return
    }
    setNameError(null)

    try {
      setPhase('creating')
      setProgress(5)
      const tr = await createTranscription({ case_id: caseId, title: trimmed, language })

      setPhase('preparing')
      setProgress(10)
      const { upload_url } = await getUploadUrl(tr.id)

      setPhase('uploading')
      await uploadWithProgress(upload_url, file, setProgress)

      setPhase('confirming')
      setProgress(95)
      await confirmUpload(tr.id)

      setProgress(100)
      toast.success('Transcription lancée !')
      setOpen(false)
      reset()
      onSuccess()
      router.push(`/transcriptions/${tr.id}`)
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Erreur inattendue'
      toast.error(msg)
      setPhase('idle')
      setProgress(0)
    }
  }

  const progressLabel =
    phase === 'uploading'
      ? `Téléchargement... ${progress}%`
      : PHASE_LABELS[phase]

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogTrigger asChild>
        <Button size="sm">Nouvelle transcription</Button>
      </DialogTrigger>

      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Nouvelle transcription</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Name */}
          <div className="space-y-1.5">
            <Label htmlFor="tr-name">Nom</Label>
            <Input
              id="tr-name"
              value={name}
              onChange={(e) => {
                setName(e.target.value)
                if (nameError) setNameError(null)
              }}
              placeholder="Ex : Audition 27/04/2026"
              disabled={isUploading}
              maxLength={200}
            />
            {nameError && <p className="text-xs text-destructive">{nameError}</p>}
          </div>

          {/* Drop zone */}
          {!file ? (
            <div
              role="button"
              tabIndex={0}
              aria-label="Zone de dépôt de fichier audio"
              className={[
                'flex flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed p-8 text-sm transition-colors cursor-pointer',
                isDragging
                  ? 'border-primary bg-primary/5'
                  : 'border-muted-foreground/30 hover:border-primary/50',
              ].join(' ')}
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              onKeyDown={(e) => e.key === 'Enter' && fileInputRef.current?.click()}
            >
              <Upload className="h-8 w-8 text-muted-foreground" />
              <div className="text-center">
                <p className="font-medium">Déposez votre fichier audio ici ou cliquez pour parcourir</p>
                <p className="text-xs text-muted-foreground mt-1">
                  {ALLOWED_EXTENSIONS.join(', ')} · max 500 Mo
                </p>
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept={ALLOWED_EXTENSIONS.join(',')}
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0]
                  if (f) selectFile(f)
                  e.target.value = ''
                }}
              />
            </div>
          ) : (
            <div className="flex items-start gap-3 rounded-lg border p-3">
              <FileAudio className="mt-0.5 h-5 w-5 shrink-0 text-muted-foreground" />
              <div className="flex-1 min-w-0">
                <p className="truncate text-sm font-medium">{file.name}</p>
                <p className="text-xs text-muted-foreground">
                  {formatFileSize(file.size)}
                  {duration != null && ` · ${formatDuration(duration)}`}
                </p>
              </div>
              {!isUploading && (
                <button
                  onClick={() => { setFile(null); setDuration(null); setName('') }}
                  className="shrink-0 text-muted-foreground hover:text-foreground"
                  aria-label="Retirer le fichier"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>
          )}

          {/* Language */}
          <div className="space-y-1.5">
            <Label htmlFor="tr-lang">Langue</Label>
            <select
              id="tr-lang"
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              disabled={isUploading}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <option value="fr">Français</option>
              <option value="en">Anglais</option>
              <option value="auto">Détection automatique</option>
            </select>
          </div>

          {/* Progress bar */}
          {isUploading && (
            <div className="space-y-1.5">
              <p className="text-xs text-muted-foreground">{progressLabel}</p>
              <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full bg-primary transition-all duration-300"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          )}

          {/* Submit */}
          <Button
            className="w-full"
            onClick={handleSubmit}
            disabled={!canSubmit}
          >
            {isUploading ? progressLabel : 'Démarrer la transcription'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
