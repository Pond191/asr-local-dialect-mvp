'use client'

import React, { useState, useRef, useEffect } from 'react'

type Seg = { start: number; end: number; text: string; avg_logprob?: number }
type ApiResp = {
  result: { language?: string; duration?: number; segments: Seg[] }
  files?: { srt?: string; vtt?: string }
}

// แปลงวินาที -> 00:01:07
function formatTime(sec: number): string {
  if (!Number.isFinite(sec)) sec = 0
  const total = Math.max(0, Math.floor(sec))
  const h = Math.floor(total / 3600)
  const m = Math.floor((total % 3600) / 60)
  const s = total % 60
  return [h, m, s].map(v => v.toString().padStart(2, '0')).join(':')
}

// แปลงขนาดไฟล์
function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
}

export default function Page() {
  const [file, setFile] = useState<File | null>(null)
  const [mode, setMode] = useState<'none' | 'dialect' | 'standard'>('standard')
  const [dialect, setDialect] = useState<'isan' | 'kham_mueang' | 'pak_tai'>('isan')
  const [language, setLanguage] = useState<string>('Thai')
  const [busy, setBusy] = useState(false)
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<ApiResp | null>(null)
  const [retryCount, setRetryCount] = useState(0)

  const abortControllerRef = useRef<AbortController | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const fakeProgressTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const API = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'
  const MAX_RETRIES = 3
  const MAX_FILE_SIZE = 500 * 1024 * 1024 // 500MB

  // ---------------- fake progress (ไม่ให้ค้างที่เลขเดิม) ----------------
  const startFakeProgress = () => {
    setProgress(15)
    if (fakeProgressTimerRef.current) {
      clearInterval(fakeProgressTimerRef.current)
    }
    fakeProgressTimerRef.current = setInterval(() => {
      setProgress(prev => {
        if (prev >= 90) return prev
        return prev + 1
      })
    }, 900)
  }

  const stopFakeProgress = () => {
    if (fakeProgressTimerRef.current) {
      clearInterval(fakeProgressTimerRef.current)
      fakeProgressTimerRef.current = null
    }
  }

  const cancelUpload = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    stopFakeProgress()
    setBusy(false)
    setProgress(0)
    setError('ยกเลิกการอัปโหลดแล้ว')
  }

  async function uploadWithRetry(formData: FormData, retries: number = 0): Promise<Response> {
    try {
      abortControllerRef.current = new AbortController()

      const res = await fetch(`${API}/transcribe`, {
        method: 'POST',
        body: formData,
        signal: abortControllerRef.current.signal,
      })

      if (!res.ok) {
        const errorText = await res.text()
        throw new Error(`HTTP ${res.status}: ${errorText}`)
      }

      return res
    } catch (err: any) {
      if (err.name === 'AbortError') {
        throw err
      }

      if (retries < MAX_RETRIES) {
        setRetryCount(retries + 1)
        setError(`เกิดข้อผิดพลาด กำลังลองใหม่ (${retries + 1}/${MAX_RETRIES})...`)
        await new Promise(resolve => setTimeout(resolve, 2000 * (retries + 1)))
        return uploadWithRetry(formData, retries + 1)
      }

      throw err
    }
  }

  async function onSubmit() {
    setError(null)
    setResult(null)
    setProgress(0)
    setRetryCount(0)

    if (!file) {
      setError('กรุณาเลือกไฟล์เสียงหรือวิดีโอก่อน')
      return
    }

    if (file.size > MAX_FILE_SIZE) {
      setError(
        `ไฟล์ใหญ่เกินไป (สูงสุด ${formatFileSize(
          MAX_FILE_SIZE
        )}) ไฟล์ของคุณ: ${formatFileSize(file.size)}`
      )
      return
    }

    const validTypes = ['audio/', 'video/']
    if (!validTypes.some(type => file.type.startsWith(type))) {
      setError('กรุณาเลือกไฟล์เสียงหรือวิดีโอเท่านั้น')
      return
    }

    setBusy(true)
    startFakeProgress()

    try {
      const form = new FormData()
      form.append('file', file)
      form.append('mode', mode)
      form.append('dialect', dialect)
      if (language.trim()) {
        form.append('language', language.trim())
      }

      const res = await uploadWithRetry(form)
      const data = (await res.json()) as ApiResp

      setResult(data)
      setError(null)
      stopFakeProgress()
      setProgress(100)
    } catch (e: any) {
      stopFakeProgress()
      if (e?.name === 'AbortError') {
        setError('ยกเลิกการอัปโหลดแล้ว')
      } else if (e?.message?.includes('413')) {
        setError(`ไฟล์ใหญ่เกินไป กรุณาใช้ไฟล์ที่เล็กกว่า ${formatFileSize(MAX_FILE_SIZE)}`)
      } else if (e?.message?.includes('timeout') || e?.message?.includes('network')) {
        setError('หมดเวลาการเชื่อมต่อ กรุณาตรวจสอบอินเทอร์เน็ตและลองใหม่')
      } else {
        setError(e?.message || 'เกิดข้อผิดพลาดไม่ทราบสาเหตุ กรุณาลองใหม่อีกครั้ง')
      }
      setProgress(0)
    } finally {
      setBusy(false)
      abortControllerRef.current = null
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

  function resetForm() {
    setFile(null)
    setResult(null)
    setError(null)
    setProgress(0)
    setRetryCount(0)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const segments = result?.result?.segments ?? []

  useEffect(() => {
    return () => {
      stopFakeProgress()
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }
    }
  }, [])

  return (
    <main
      style={{
        minHeight: '100vh',
        background: 'linear-gradient(135deg,#e0e7ff 0%,#c7d2fe 40%,#c4b5fd 100%)',
        fontFamily: '-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif',
        padding: '32px 16px',
        color: '#111827',
      }}
    >
      <div style={{ maxWidth: 960, margin: '0 auto' }}>
        {/* HEADER */}
        <header style={{ textAlign: 'center', marginBottom: 28 }}>
          <h1
            style={{
              fontSize: 40,
              fontWeight: 800,
              color: '#ffffffff',
              textShadow: '0 12px 30px rgba(15,23,42,0.4)',
              marginBottom: 8,
            }}
          >
            ASR Local Dialect
          </h1>
          <p
            style={{
              fontSize: 14,
              color: '#575758ff',
              lineHeight: 1.7,
            }}
          >
            ระบบถอดเสียงภาษาไทยและภาษาถิ่น (อีสาน, คำเมือง, ใต้) รองรับไฟล์ใหญ่ถึง 500MB
          </p>
        </header>

        {/* CARD */}
        <section
          style={{
            background: '#ffffff',
            borderRadius: 24,
            padding: 28,
            boxShadow: '0 20px 50px rgba(15,23,42,0.18)',
            border: '1px solid #e5e7eb',
            margin: '0 auto',
          }}
        >
          {/* TITLE BAR */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              fontSize: 16,
              fontWeight: 600,
              marginBottom: 16,
              color: '#111827',
            }}
          >
            <span>📁</span>
            <span>อัปโหลดไฟล์</span>
          </div>

          {/* UPLOAD AREA */}
          <div
            style={{
              borderRadius: 18,
              border: '2px dashed #d4d4ff',
              background: '#f8fafc',
              padding: 24,
              marginBottom: 24,
            }}
          >
            <div style={{ textAlign: 'center' }}>
              <input
                ref={fileInputRef}
                type="file"
                accept="audio/*,video/*"
                onChange={e => {
                  const selectedFile = e.target.files?.[0] || null
                  setFile(selectedFile)
                  setError(null)
                  setResult(null)
                }}
                style={{
                  display: 'block',
                  margin: '0 auto 12px',
                  fontSize: 13,
                }}
              />

              {file ? (
                <div
                  style={{
                    marginTop: 8,
                    padding: 12,
                    borderRadius: 12,
                    background: '#f3faf7',
                    border: '1px solid #bbf7d0',
                    color: '#166534',
                    fontSize: 13,
                  }}
                >
                  <div style={{ fontWeight: 600 }}>ไฟล์: {file.name}</div>
                  <div style={{ marginTop: 4, color: '#166534' }}>
                    ขนาด: {formatFileSize(file.size)} | ประเภท: {file.type || 'ไม่ระบุ'}
                  </div>
                </div>
              ) : (
                <p style={{ fontSize: 13, color: '#6b7280' }}>
                  รองรับ .mp3, .wav, .m4a, .mp4, .mpeg, .webm, .ogg, .flac (สูงสุด 500MB)
                </p>
              )}
            </div>
          </div>

          {/* SETTINGS */}
          <div style={{ marginBottom: 20 }}>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit,minmax(220px,1fr))',
                gap: 16,
                marginBottom: 14,
              }}
            >
              <div>
                <label
                  style={{
                    display: 'block',
                    fontSize: 13,
                    fontWeight: 600,
                    marginBottom: 6,
                    color: '#374151',
                  }}
                >
                  โหมดผลลัพธ์
                </label>
                <select
                  value={mode}
                  onChange={e => setMode(e.target.value as any)}
                  style={{
                    width: '100%',
                    padding: '8px 10px',
                    borderRadius: 10,
                    border: '1px solid #d1d5db',
                    fontSize: 13,
                    background: '#ffffff',
                  }}
                >
                  <option value="none">แสดงตามที่โมเดลถอด</option>
                  <option value="dialect">เน้นรูปแบบภาษาถิ่น</option>
                  <option value="standard">แปลงเป็นภาษาไทยกลาง</option>
                </select>
              </div>

              <div>
                <label
                  style={{
                    display: 'block',
                    fontSize: 13,
                    fontWeight: 600,
                    marginBottom: 6,
                    color: '#374151',
                  }}
                >
                  ภาษาถิ่น
                </label>
                <select
                  value={dialect}
                  onChange={e => setDialect(e.target.value as any)}
                  style={{
                    width: '100%',
                    padding: '8px 10px',
                    borderRadius: 10,
                    border: '1px solid #d1d5db',
                    fontSize: 13,
                    background: '#ffffff',
                  }}
                >
                  <option value="isan">อีสาน (Isan)</option>
                  <option value="kham_mueang">คำเมือง (Northern)</option>
                  <option value="pak_tai">ใต้ (Southern)</option>
                </select>
              </div>
            </div>

            <div>
              <label
                style={{
                  display: 'block',
                  fontSize: 13,
                  fontWeight: 600,
                  marginBottom: 6,
                  color: '#374151',
                }}
              >
                คำใบ้ภาษา (Initial Prompt)
              </label>
              <input
                value={language}
                onChange={e => setLanguage(e.target.value)}
                placeholder="เช่น Thai, Thai / Isan dialect"
                style={{
                  width: '100%',
                  padding: '8px 10px',
                  borderRadius: 10,
                  border: '1px solid #d1d5db',
                  fontSize: 13,
                  background: '#ffffff',
                }}
              />
              <p style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>
                ช่องนี้เป็นตัวช่วยบอกโมเดลว่าในไฟล์น่าจะเป็นภาษาอะไร เช่น Thai, Thai / Isan dialect
              </p>
            </div>
          </div>

          {/* PROGRESS */}
          {(busy || progress > 0) && (
            <div style={{ marginBottom: 18 }}>
              <div
                style={{
                  height: 8,
                  background: '#e5e7eb',
                  borderRadius: 999,
                  overflow: 'hidden',
                }}
              >
                <div
                  style={{
                    height: '100%',
                    width: `${progress}%`,
                    background: '#6366f1',
                    transition: 'width 0.3s ease',
                  }}
                />
              </div>
              <div
                style={{
                  marginTop: 6,
                  fontSize: 12,
                  color: '#6b7280',
                  display: 'flex',
                  justifyContent: 'space-between',
                }}
              >
                <span>
                  {busy
                    ? 'กำลังประมวลผลไฟล์...'
                    : progress === 100
                    ? 'ถอดเสียงเสร็จเรียบร้อย'
                    : 'เตรียมไฟล์...'}
                  {retryCount > 0 && ` · ลองใหม่อัตโนมัติ ${retryCount} ครั้ง`}
                </span>
                <span>{progress}%</span>
              </div>
            </div>
          )}

          {/* BUTTONS */}
          <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginTop: 8 }}>
            <button
              onClick={onSubmit}
              disabled={busy || !file}
              style={{
                flex: 1,
                padding: '12px 20px',
                borderRadius: 999,
                border: 'none',
                background:
                  busy || !file
                    ? '#cbd5f5'
                    : 'linear-gradient(90deg,#6366f1,#8b5cf6)',
                color: busy || !file ? '#4b5563' : '#ffffff',
                fontWeight: 600,
                fontSize: 15,
                cursor: busy || !file ? 'not-allowed' : 'pointer',
                boxShadow:
                  busy || !file ? 'none' : '0 14px 32px rgba(79,70,229,0.35)',
              }}
            >
              {busy ? 'กำลังถอดเสียง...' : 'เริ่มถอดเสียง'}
            </button>

            {busy && (
              <button
                onClick={cancelUpload}
                style={{
                  padding: '10px 16px',
                  borderRadius: 999,
                  border: '1px solid #ef4444',
                  background: '#ffffff',
                  color: '#b91c1c',
                  fontWeight: 500,
                  fontSize: 13,
                  cursor: 'pointer',
                }}
              >
                ยกเลิก
              </button>
            )}

            {result && !busy && (
              <button
                onClick={resetForm}
                style={{
                  padding: '10px 16px',
                  borderRadius: 999,
                  border: '1px solid #d1d5db',
                  background: '#ffffff',
                  color: '#4b5563',
                  fontWeight: 500,
                  fontSize: 13,
                  cursor: 'pointer',
                }}
              >
                ล้างค่าใหม่
              </button>
            )}
          </div>

          {/* ERROR */}
          {error && (
            <div
              style={{
                marginTop: 14,
                padding: 10,
                borderRadius: 10,
                background: '#fef2f2',
                border: '1px solid #fecaca',
                color: '#991b1b',
                fontSize: 13,
              }}
            >
              ⚠️ {error}
            </div>
          )}
        </section>

        {/* RESULT SECTION */}
        {result && (
          <section
            style={{
              background: '#ffffff',
              borderRadius: 20,
              padding: 22,
              boxShadow: '0 18px 40px rgba(15,23,42,0.14)',
              border: '1px solid #e5e7eb',
              marginTop: 20,
            }}
          >
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                gap: 12,
                marginBottom: 14,
                flexWrap: 'wrap',
              }}
            >
              <h2 style={{ fontSize: 18, fontWeight: 600, color: '#111827' }}>
                ผลลัพธ์การถอดเสียง
              </h2>

              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {result.files?.srt && (
                  <button
                    onClick={() => downloadText(result.files!.srt!, 'transcript.srt')}
                    style={{
                      padding: '6px 12px',
                      borderRadius: 999,
                      border: '1px solid #6366f1',
                      background: '#eef2ff',
                      color: '#4338ca',
                      fontSize: 13,
                      fontWeight: 500,
                      cursor: 'pointer',
                    }}
                  >
                    ดาวน์โหลด .srt
                  </button>
                )}
                {result.files?.vtt && (
                  <button
                    onClick={() => downloadText(result.files!.vtt!, 'transcript.vtt')}
                    style={{
                      padding: '6px 12px',
                      borderRadius: 999,
                      border: '1px solid #6366f1',
                      background: '#eef2ff',
                      color: '#4338ca',
                      fontSize: 13,
                      fontWeight: 500,
                      cursor: 'pointer',
                    }}
                  >
                    ดาวน์โหลด .vtt
                  </button>
                )}
              </div>
            </div>

            {/* INFO */}
            <div
              style={{
                display: 'flex',
                gap: 18,
                flexWrap: 'wrap',
                padding: 10,
                borderRadius: 12,
                background: '#f9fafb',
                border: '1px solid #e5e7eb',
                marginBottom: 14,
              }}
            >
              <div>
                <div style={{ fontSize: 11, color: '#6b7280' }}>ภาษา</div>
                <div style={{ fontSize: 14, fontWeight: 600 }}>
                  {result.result.language || '-'}
                </div>
              </div>
              <div>
                <div style={{ fontSize: 11, color: '#6b7280' }}>ระยะเวลา</div>
                <div style={{ fontSize: 14, fontWeight: 600 }}>
                  {result.result.duration ? formatTime(result.result.duration) : '-'}
                </div>
              </div>
              <div>
                <div style={{ fontSize: 11, color: '#6b7280' }}>จำนวน segments</div>
                <div style={{ fontSize: 14, fontWeight: 600 }}>{segments.length}</div>
              </div>
            </div>

            {/* SEGMENTS */}
            <div style={{ maxHeight: 460, overflowY: 'auto' }}>
              {segments.map((s, idx) => (
                <div
                  key={`${s.start}-${s.end}-${idx}`}
                  style={{
                    padding: 12,
                    marginBottom: 10,
                    borderRadius: 10,
                    border: '1px solid #e5e7eb',
                    background: '#ffffff',
                  }}
                >
                  <div
                    style={{
                      fontSize: 12,
                      color: '#6b7280',
                      marginBottom: 6,
                      display: 'flex',
                      justifyContent: 'space-between',
                    }}
                  >
                    <span>
                      {formatTime(s.start)} → {formatTime(s.end)}
                    </span>
                    {typeof s.avg_logprob === 'number' && (
                      <span>avg_logprob: {s.avg_logprob.toFixed(2)}</span>
                    )}
                  </div>
                  <textarea
                    value={s.text}
                    onChange={e => {
                      const newText = e.target.value
                      setResult(prev => {
                        if (!prev) return prev
                        const newSegs = [...(prev.result.segments ?? [])]
                        newSegs[idx] = { ...newSegs[idx], text: newText }
                        return {
                          ...prev,
                          result: { ...prev.result, segments: newSegs },
                        }
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
          </section>
        )}
      </div>
    </main>
  )
}
