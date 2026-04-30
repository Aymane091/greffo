import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

vi.mock('next/navigation', () => ({
  useRouter: vi.fn(() => ({ push: vi.fn() })),
  usePathname: vi.fn(() => '/cases/case-1'),
  useSearchParams: vi.fn(() => new URLSearchParams()),
}))

vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }))

vi.mock('@/lib/api/transcriptions', () => ({
  createTranscription: vi.fn(),
  getUploadUrl: vi.fn(),
  confirmUpload: vi.fn(),
}))

vi.mock('@/lib/utils/audio-duration', () => ({
  getAudioDuration: vi.fn().mockResolvedValue(30),
}))

import { UploadDialog } from '@/components/transcriptions/upload-dialog'
import { createTranscription, getUploadUrl, confirmUpload } from '@/lib/api/transcriptions'
import { toast } from 'sonner'

function wrap(ui: React.ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>)
}

describe('UploadDialog', () => {
  beforeEach(() => vi.clearAllMocks())

  it('renders trigger button', () => {
    wrap(<UploadDialog caseId="case-1" onSuccess={vi.fn()} />)
    expect(screen.getByRole('button', { name: 'Nouvelle transcription' })).toBeDefined()
  })

  it('opens dialog on trigger click', async () => {
    wrap(<UploadDialog caseId="case-1" onSuccess={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: 'Nouvelle transcription' }))
    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeDefined()
    })
    expect(screen.getByLabelText('Nom')).toBeDefined()
    expect(screen.getByLabelText('Zone de dépôt de fichier audio')).toBeDefined()
  })

  it('rejects file with invalid MIME type', async () => {
    wrap(<UploadDialog caseId="case-1" onSuccess={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: 'Nouvelle transcription' }))
    await waitFor(() => screen.getByRole('dialog'))

    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const badFile = new File(['data'], 'document.pdf', { type: 'application/pdf' })
    fireEvent.change(input, { target: { files: [badFile] } })

    await waitFor(() => {
      expect(vi.mocked(toast.error)).toHaveBeenCalledWith(
        expect.stringContaining('Format non supporté'),
      )
    })
  })

  it('rejects file exceeding 500 MB', async () => {
    wrap(<UploadDialog caseId="case-1" onSuccess={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: 'Nouvelle transcription' }))
    await waitFor(() => screen.getByRole('dialog'))

    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const bigFile = new File(['x'], 'big.mp3', { type: 'audio/mpeg' })
    Object.defineProperty(bigFile, 'size', { value: 600 * 1024 * 1024 })
    fireEvent.change(input, { target: { files: [bigFile] } })

    await waitFor(() => {
      expect(vi.mocked(toast.error)).toHaveBeenCalledWith(
        expect.stringContaining('volumineux'),
      )
    })
  })

  it('pre-fills name from filename stem on valid file selection', async () => {
    wrap(<UploadDialog caseId="case-1" onSuccess={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: 'Nouvelle transcription' }))
    await waitFor(() => screen.getByRole('dialog'))

    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const mp3 = new File(['ID3'], 'audition-dupont.mp3', { type: 'audio/mpeg' })
    fireEvent.change(input, { target: { files: [mp3] } })

    await waitFor(() => {
      const nameInput = screen.getByLabelText('Nom') as HTMLInputElement
      expect(nameInput.value).toBe('audition-dupont')
    })
  })

  it('submit button is disabled when name < 3 chars', async () => {
    wrap(<UploadDialog caseId="case-1" onSuccess={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: 'Nouvelle transcription' }))
    await waitFor(() => screen.getByRole('dialog'))

    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const mp3 = new File(['ID3'], 'ok.mp3', { type: 'audio/mpeg' })
    fireEvent.change(input, { target: { files: [mp3] } })

    await waitFor(() => {
      const ni = screen.getByLabelText('Nom') as HTMLInputElement
      expect(ni.value).toBe('ok')
    })

    const nameInput = screen.getByLabelText('Nom') as HTMLInputElement
    fireEvent.change(nameInput, { target: { value: 'AB' } })

    const submitBtn = screen.getByRole('button', { name: 'Démarrer la transcription' })
    expect((submitBtn as HTMLButtonElement).disabled).toBe(true)
  })

  it('starts upload sequence: calls createTranscription then getUploadUrl on valid submit', async () => {
    vi.mocked(createTranscription).mockResolvedValue({ id: 'tr-new' } as never)
    // Reject at getUploadUrl to stop flow before XHR — verifies steps 1 + 2 and error recovery
    vi.mocked(getUploadUrl).mockRejectedValue(new Error('stop'))

    wrap(<UploadDialog caseId="case-1" onSuccess={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: 'Nouvelle transcription' }))
    await waitFor(() => screen.getByRole('dialog'))

    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const mp3 = new File(['ID3'], 'audition.mp3', { type: 'audio/mpeg' })
    fireEvent.change(input, { target: { files: [mp3] } })

    await waitFor(() => {
      const nameInput = screen.getByLabelText('Nom') as HTMLInputElement
      expect(nameInput.value).toBe('audition')
    })

    fireEvent.click(screen.getByRole('button', { name: 'Démarrer la transcription' }))

    await waitFor(() => expect(vi.mocked(createTranscription)).toHaveBeenCalledWith({
      case_id: 'case-1', title: 'audition', language: 'fr',
    }))
    await waitFor(() => expect(vi.mocked(getUploadUrl)).toHaveBeenCalledWith('tr-new'))
    // Error caught → toast.error, button re-enabled
    await waitFor(() => expect(vi.mocked(toast.error)).toHaveBeenCalled())
  })
})
