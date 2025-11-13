import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

// URL backend ที่ Render (ตั้งจากตัวแปร env ถ้าไม่มีก็ fallback เป็น localhost)
const API =
  process.env.ASR_BACKEND_URL || 'http://127.0.0.1:8000'

export async function POST(req: NextRequest) {
  try {
    const formData = await req.formData()

    const resp = await fetch(`${API}/transcribe`, {
      method: 'POST',
      body: formData,
    })

    const text = await resp.text()
    let json: any = null
    try {
      json = JSON.parse(text)
    } catch {
      // ถ้า parse JSON ไม่ได้ ก็ส่งข้อความดิบกลับไป
    }

    return new NextResponse(json ? JSON.stringify(json) : text, {
      status: resp.status,
      headers: {
        'Content-Type': json ? 'application/json' : 'text/plain',
      },
    })
  } catch (e: any) {
    console.error('Proxy /api/transcribe error:', e)
    return NextResponse.json(
      { error: e?.message || 'Proxy failed: fetch failed' },
      { status: 500 },
    )
  }
}
