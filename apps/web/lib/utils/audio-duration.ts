const TIMEOUT_MS = 5_000

export async function getAudioDuration(file: File): Promise<number | null> {
  return new Promise((resolve) => {
    const url = URL.createObjectURL(file)
    const audio = new Audio()

    const cleanup = (result: number | null) => {
      clearTimeout(timer)
      audio.src = ''
      URL.revokeObjectURL(url)
      resolve(result)
    }

    const timer = setTimeout(() => cleanup(null), TIMEOUT_MS)

    audio.addEventListener('loadedmetadata', () => {
      const d = audio.duration
      cleanup(isFinite(d) && d > 0 ? Math.round(d) : null)
    })

    audio.addEventListener('error', () => cleanup(null))
    audio.src = url
  })
}
