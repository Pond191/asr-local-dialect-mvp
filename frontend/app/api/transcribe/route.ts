// frontend/app/api/transcribe/route.ts
import { NextRequest, NextResponse } from 'next/server'

export const runtime = 'nodejs'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'

export async function POST(req: NextRequest) {
  try {
    const formData = await req.formData()
    const r = await fetch(`${API}/transcribe`, {
      method: 'POST',
      body: formData,
    })

    const buf = await r.arrayBuffer()
    const headers = new Headers()
    headers.set('Content-Type', r.headers.get('content-type') || 'application/json')

    return new NextResponse(buf, { status: r.status, headers })
  } catch (e: any) {
    return NextResponse.json(
      { error: `Proxy failed: ${e?.message || e}` },
      { status: 502 },
    )
  }
}
