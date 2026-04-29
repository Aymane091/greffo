import { auth } from '@/lib/auth'
import { NextResponse } from 'next/server'

const handler = auth((req) => {
  const { pathname } = req.nextUrl

  if (pathname.startsWith('/dashboard') && !req.auth) {
    const loginUrl = new URL('/login', req.url)
    loginUrl.searchParams.set('callbackUrl', req.url)
    return NextResponse.redirect(loginUrl)
  }

  return NextResponse.next()
})

export const proxy = handler
export default handler

export const config = {
  matcher: ['/dashboard/:path*'],
}
