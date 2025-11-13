// frontend/app/api/transcribe/route.ts
import { NextRequest, NextResponse } from 'next/server'

export const runtime = 'nodejs'         // ต้องเป็น node เพื่อรองรับไฟล์ใหญ่
export const dynamic = 'force-dynamic'  // กัน cache ระหว่าง dev

const API = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'

export async function POST(req: NextRequest) {
  try {
    const formData = await req.formData()

    // ตั้ง timeout ยาวสำหรับไฟล์ใหญ่
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 1000 * 60 * 10) // 10 นาที

    const r = await fetch(`${API}/transcribe`, {
      method: 'POST',
      body: formData,
      signal: controller.signal,
    })
    clearTimeout(timeout)

    const buf = await r.arrayBuffer()
    const headers = new Headers()
    headers.set('Content-Type', r.headers.get('content-type') || 'application/json')
    return new NextResponse(buf, { status: r.status, headers })
  } catch (e: any) {
    return NextResponse.json({ error: `Proxy failed: ${e?.message || 'fetch failed'}` }, { status: 502 })
  }
}
