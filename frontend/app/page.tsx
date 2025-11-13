'use client'

import React, { useState } from 'react'

type Seg = { start: number; end: number; text: string; avg_logprob?: number }
type ApiResp = {
  result: { language?: string; duration?: number; segments: Seg[] }
  files?: { srt?: string; vtt?: string }
}

/** แปลงวินาที -> เวลาแบบ h:mm:ss เช่น 0:01:07 */
function formatTime(t: number): string {
  if (!Number.isFinite(t)) return '0:00:00'
  const total = Math.max(0, Math.floor(t)) // ปัดลงเป็นวินาทีเต็ม
  const h = Math.floor(total / 3600)
  const m = Math.floor((total % 3600) / 60)
  const s = total % 60
  return `${h}:${m.toString().padStart(2, '0')}:${s
    .toString()
    .padStart(2, '0')}`
}

export default function Page() {
  const [file, setFile] = useState<File | null>(null)
  const [mode, setMode] = useState<'none' | 'dialect' | 'standard'>('standard')
  const [dialect, setDialect] = useState<'isan' | 'kham_mueang' | 'pak_tai'>('isan')
  const [language, setLanguage] = useState<string>('Thai / Isan dialect')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<ApiResp | null>(null)

  // ใช้ URL ของ backend ที่อยู่บน Render
  const API = 'https://asr-local-dialect-mvp.onrender.com'


  async function onSubmit() {
    setError(null)
    setResult(null)

    if (!file) {
      setError('กรุณาเลือกไฟล์เสียงหรือวิดีโอก่อน')
      return
    }

    setBusy(true)
    try {
      const form = new FormData()
      form.append('file', file)
      form.append('mode', mode)
      form.append('dialect', dialect)
      if (language.trim()) {
        form.append('language', language.trim())
      }

      const controller = new AbortController()
      const timeout = setTimeout(() => controller.abort(), 1000 * 60 * 10) // 10 นาที
      const res = await fetch(`${API}/transcribe`, {
        method: 'POST',
        body: form,
        signal: controller.signal,
      })
      clearTimeout(timeout)

      if (!res.ok) {
        const txt = await res.text()
        throw new Error(`เซิร์ฟเวอร์ตอบกลับผิดพลาด (HTTP ${res.status}) : ${txt}`)
      }

      const data = (await res.json()) as ApiResp
      setResult(data)
    } catch (e: any) {
      if (e?.name === 'AbortError') {
        setError('ใช้เวลาดำเนินการนานเกินไป (timeout) กรุณาลองใหม่ หรือลองใช้ไฟล์ที่สั้นลง')
      } else {
        setError(e?.message || 'เกิดข้อผิดพลาดระหว่างอัปโหลดหรือถอดเสียง')
      }
    } finally {
      setBusy(false)
    }
  }

  function downloadText(text: string, filename: string) {
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  }

  const segments = result?.result?.segments ?? []

  return (
    <main
      style={{
        minHeight: '100vh',
        background: '#f5f5f7',
        fontFamily:
          '-apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif',
      }}
    >
      <div
        style={{
          maxWidth: 960,
          margin: '0 auto',
          padding: '32px 16px 48px',
        }}
      >
        {/* Header */}
        <header style={{ marginBottom: 24 }}>
          <h1
            style={{
              fontSize: 32,
              fontWeight: 700,
              marginBottom: 8,
              color: '#111827',
            }}
          >
            ASR Local Dialect — MVP
          </h1>
          <p style={{ color: '#4b5563', lineHeight: 1.6, maxWidth: 720 }}>
            ระบบตัวอย่างสำหรับถอดเสียงจากไฟล์เสียงหรือวิดีโอเป็นข้อความภาษาไทย
            และภาษาถิ่น (อีสาน, คำเมือง, ใต้) 
            
          </p>
        </header>

        {/* Input card */}
        <section
          style={{
            background: '#ffffff',
            borderRadius: 16,
            padding: 20,
            boxShadow: '0 10px 25px rgba(15,23,42,0.06)',
            marginBottom: 24,
          }}
        >
          <h2
            style={{
              fontSize: 18,
              fontWeight: 600,
              marginBottom: 12,
              color: '#111827',
            }}
          >
            ขั้นตอนที่ 1: เลือกไฟล์เสียงหรือวิดีโอ
          </h2>
          <p style={{ fontSize: 14, color: '#6b7280', marginBottom: 10 }}>
            รองรับไฟล์เช่น <b>.mp3, .wav, .m4a, .mp4</b> แนะนำให้ใช้ไฟล์ไม่ยาวมาก
            เพื่อให้ถอดเสียงได้เร็วขึ้น
          </p>

          <div
            style={{
              border: '1px dashed #cbd5f5',
              borderRadius: 12,
              padding: 16,
              background: '#f9fafb',
              marginBottom: 16,
              display: 'flex',
              flexDirection: 'column',
              gap: 8,
            }}
          >
            <input
              type="file"
              accept="audio/*,video/*"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
            <span style={{ fontSize: 13, color: '#6b7280' }}>
              ไฟล์ที่เลือก:{' '}
              <b>{file ? file.name : 'ยังไม่ได้เลือกไฟล์'}</b>
            </span>
          </div>

          <h2
            style={{
              fontSize: 18,
              fontWeight: 600,
              marginBottom: 8,
              color: '#111827',
            }}
          >
            ขั้นตอนที่ 2: ตั้งค่าการถอดเสียง
          </h2>

          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: 16,
              marginBottom: 12,
            }}
          >
            <label style={{ fontSize: 14, color: '#374151' }}>
              โหมดผลลัพธ์ (mode):{' '}
              <select
                value={mode}
                onChange={(e) => setMode(e.target.value as any)}
                style={{
                  marginLeft: 4,
                  padding: '4px 8px',
                  borderRadius: 8,
                  border: '1px solid #d1d5db',
                }}
              >
                <option value="none">แสดงตามที่โมเดลถอด</option>
                <option value="dialect">เน้นรูปแบบภาษาถิ่น</option>
                <option value="standard">แปลงเป็นภาษาไทยกลาง</option>
              </select>
            </label>

            <label style={{ fontSize: 14, color: '#374151' }}>
              ภาษาถิ่น (dialect):{' '}
              <select
                value={dialect}
                onChange={(e) => setDialect(e.target.value as any)}
                style={{
                  marginLeft: 4,
                  padding: '4px 8px',
                  borderRadius: 8,
                  border: '1px solid #d1d5db',
                }}
              >
                <option value="isan">อีสาน (Isan)</option>
                <option value="kham_mueang">คำเมือง / เหนือ (Kham Mueang)</option>
                <option value="pak_tai">ใต้ (Southern Thai)</option>
              </select>
            </label>
          </div>

          <div style={{ marginBottom: 16 }}>
            <label
              style={{
                display: 'block',
                fontSize: 14,
                color: '#374151',
                marginBottom: 4,
              }}
            >
              initial_prompt (language):{' '}
            </label>
            <input
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              placeholder="เช่น: Thai / Isan dialect, หรือ Thai language"
              style={{
                width: '100%',
                maxWidth: 480,
                padding: '6px 10px',
                borderRadius: 8,
                border: '1px solid #d1d5db',
                fontSize: 14,
              }}
            />
            <p style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>
              ช่องนี้เป็นตัวช่วยบอกโมเดลว่าเสียงเป็นภาษาอะไร เช่น{' '}
              <code>Thai</code>, <code>Thai / Isan dialect</code>,{' '}
              <code>English</code> ถ้าไม่แน่ใจปล่อยค่าเดิมไว้ได้
            </p>
          </div>

          <h2
            style={{
              fontSize: 18,
              fontWeight: 600,
              marginBottom: 8,
              color: '#111827',
            }}
          >
            ขั้นตอนที่ 3: เริ่มถอดเสียง
          </h2>

          <button
            onClick={onSubmit}
            disabled={busy || !file}
            style={{
              padding: '10px 20px',
              borderRadius: 999,
              border: 'none',
              background: busy || !file ? '#9ca3af' : '#2563eb',
              color: '#ffffff',
              fontWeight: 600,
              fontSize: 15,
              cursor: busy || !file ? 'not-allowed' : 'pointer',
              boxShadow: busy || !file ? 'none' : '0 8px 20px rgba(37,99,235,0.35)',
              transition: 'transform 0.05s ease, box-shadow 0.05s ease',
            }}
          >
            {busy ? 'กำลังถอดเสียง โปรดรอสักครู่...' : 'อัปโหลด & ถอดเสียง'}
          </button>

          {error && (
            <p
              style={{
                marginTop: 12,
                color: '#b91c1c',
                fontSize: 14,
                background: '#fee2e2',
                borderRadius: 8,
                padding: '8px 10px',
              }}
            >
              ⚠️ {error}
            </p>
          )}

          {!error && busy && (
            <p
              style={{
                marginTop: 12,
                color: '#4b5563',
                fontSize: 14,
              }}
            >
              กำลังประมวลผลไฟล์ของคุณ… สำหรับไฟล์ยาวอาจใช้เวลาหลายนาที
            </p>
          )}
        </section>

        {/* Result section */}
        <section
          style={{
            background: '#ffffff',
            borderRadius: 16,
            padding: 20,
            boxShadow: '0 10px 25px rgba(15,23,42,0.05)',
          }}
        >
          <h2
            style={{
              fontSize: 20,
              fontWeight: 600,
              marginBottom: 12,
              color: '#111827',
            }}
          >
            ผลลัพธ์การถอดเสียง
          </h2>

          {!result && !busy && (
            <p style={{ fontSize: 14, color: '#6b7280' }}>
              เมื่อระบบถอดเสียงเสร็จแล้ว ข้อความจะถูกแสดงในส่วนนี้
              คุณสามารถแก้ไขข้อความแต่ละช่วงได้ และดาวน์โหลดเป็นไฟล์ซับไตเติล
            </p>
          )}

          {result && (
            <>
              <div
                style={{
                  display: 'flex',
                  flexWrap: 'wrap',
                  gap: 12,
                  alignItems: 'center',
                  marginBottom: 12,
                }}
              >
                <div style={{ fontSize: 13, color: '#4b5563' }}>
                  <b>language:</b> {result.result.language ?? '-'}
                  {'  |  '}
                  <b>duration:</b>{' '}
                  {result.result.duration != null
                    ? `${result.result.duration.toFixed(1)} วินาที`
                    : '-'}
                  {'  |  '}
                  <b>segments:</b> {segments.length}
                </div>

                <div style={{ flexGrow: 1 }} />

                {result.files?.srt && (
                  <button
                    onClick={() => downloadText(result.files!.srt!, 'result.srt')}
                    style={{
                      padding: '6px 10px',
                      borderRadius: 999,
                      border: '1px solid #2563eb',
                      background: '#eff6ff',
                      color: '#1d4ed8',
                      fontSize: 13,
                      cursor: 'pointer',
                    }}
                  >
                    ดาวน์โหลด .srt
                  </button>
                )}
                {result.files?.vtt && (
                  <button
                    onClick={() => downloadText(result.files!.vtt!, 'result.vtt')}
                    style={{
                      padding: '6px 10px',
                      borderRadius: 999,
                      border: '1px solid #2563eb',
                      background: '#eff6ff',
                      color: '#1d4ed8',
                      fontSize: 13,
                      cursor: 'pointer',
                    }}
                  >
                    ดาวน์โหลด .vtt
                  </button>
                )}
              </div>

              <div>
                {segments.map((s, idx) => (
                  <div
                    key={idx}
                    style={{
                      padding: '10px 0',
                      borderTop: idx === 0 ? 'none' : '1px solid #e5e7eb',
                    }}
                  >
                    <div
                      style={{
                        fontSize: 12,
                        color: '#6b7280',
                        marginBottom: 4,
                      }}
                    >
                      {/* เปลี่ยนมาใช้เวลาแบบ h:mm:ss */}
                      {formatTime(s.start)} → {formatTime(s.end)}
                    </div>
                    <textarea
                      value={s.text}
                      onChange={(e) => {
                        const newSegs = [...segments]
                        newSegs[idx] = { ...newSegs[idx], text: e.target.value }
                        setResult({
                          ...result!,
                          result: { ...result!.result, segments: newSegs },
                        })
                      }}
                      style={{
                        width: '100%',
                        minHeight: 60,
                        borderRadius: 8,
                        border: '1px solid #d1d5db',
                        padding: 8,
                        fontSize: 14,
                        resize: 'vertical',
                      }}
                    />
                  </div>
                ))}
              </div>
            </>
          )}
        </section>
      </div>
    </main>
  )
}
