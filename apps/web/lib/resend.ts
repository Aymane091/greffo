import { serverEnv } from '@/lib/env'

export async function sendMagicLink(params: {
  to: string
  url: string
}): Promise<void> {
  const from = `${serverEnv.RESEND_FROM_NAME} <${serverEnv.RESEND_FROM_EMAIL}>`
  const { hostname } = new URL(params.url)

  const res = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${serverEnv.RESEND_API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      from,
      to: params.to,
      subject: `Connexion à Greffo`,
      text: [
        `Bonjour,`,
        ``,
        `Cliquez sur le lien ci-dessous pour vous connecter à Greffo :`,
        `${params.url}`,
        ``,
        `Ce lien expire dans 24 heures.`,
        ``,
        `Si vous n'avez pas demandé ce lien, ignorez cet email.`,
        ``,
        `— L'équipe Greffo (${hostname})`,
      ].join('\n'),
      html: `
        <p>Bonjour,</p>
        <p>Cliquez sur le bouton ci-dessous pour vous connecter à <strong>Greffo</strong> :</p>
        <p><a href="${params.url}" style="display:inline-block;padding:12px 24px;background:#1a1a2e;color:#fff;text-decoration:none;border-radius:6px;font-weight:600;">Se connecter</a></p>
        <p style="color:#666;font-size:13px;">Ce lien expire dans 24 heures.<br>Si vous n'avez pas demandé ce lien, ignorez cet email.</p>
      `,
    }),
  })

  if (!res.ok) {
    const body = await res.text()
    throw new Error(`Resend error ${res.status}: ${body}`)
  }
}
