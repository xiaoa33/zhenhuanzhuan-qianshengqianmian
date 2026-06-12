import { useState, useRef, useEffect, useContext } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { MusicContext } from '../App'
import './DuetPage.css'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export default function DuetPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const { muted, toggleMute } = useContext(MusicContext)

  const { charA, charB, context, starter } = location.state || {}

  const [messages, setMessages] = useState([])
  const [activeRole, setActiveRole] = useState(null)
  const [isRunning, setIsRunning] = useState(false)
  const [isDone, setIsDone] = useState(false)
  const [round, setRound] = useState(0)

  const messagesEndRef = useRef(null)
  const abortRef = useRef(null)
  const audioCtxRef = useRef(null)
  const nextTimeRef = useRef(0)

  useEffect(() => {
    if (!charA || !charB) {
      navigate('/select')
      return
    }
    startDuet()
    return () => {
      abortRef.current?.abort()
      if (audioCtxRef.current?.state !== 'closed') audioCtxRef.current?.close()
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const startDuet = async () => {
    abortRef.current?.abort()
    if (audioCtxRef.current?.state !== 'closed') audioCtxRef.current?.close()

    setMessages([])
    setRound(0)
    setIsDone(false)
    setIsRunning(true)
    setActiveRole(null)

    const abort = new AbortController()
    abortRef.current = abort

    const audioCtx = new (window.AudioContext || window.webkitAudioContext)()
    audioCtxRef.current = audioCtx
    nextTimeRef.current = audioCtx.currentTime + 0.05

    let turnCount = 0

    try {
      const resp = await fetch(`${BASE_URL}/duet/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          character_a: charA.id,
          character_b: charB.id,
          context: context || '两位角色在宫中相遇',
          starter: starter || charA.id,
          max_rounds: 10,
        }),
        signal: abort.signal,
      })

      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)

      const reader = resp.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('event: done')) {
            setIsDone(true)
            setIsRunning(false)
            setActiveRole(null)
            continue
          }
          if (!line.startsWith('data: ')) continue

          let data
          try { data = JSON.parse(line.slice(6)) } catch { continue }

          if (data.role) {
            turnCount++
            setRound(Math.ceil(turnCount / 2))
            setActiveRole(data.role)
            setMessages(prev => [...prev, { role: data.role, text: data.text, emotion: data.emotion }])
          }

          if (data.audio) {
            try {
              const arrayBuf = await fetch('data:audio/wav;base64,' + data.audio).then(r => r.arrayBuffer())
              const decoded = await audioCtx.decodeAudioData(arrayBuf)
              const src = audioCtx.createBufferSource()
              src.buffer = decoded
              src.connect(audioCtx.destination)
              const t = Math.max(audioCtx.currentTime, nextTimeRef.current)
              src.start(t)
              nextTimeRef.current = t + decoded.duration
            } catch { /* ignore audio decode errors */ }
          }
        }
      }
    } catch (err) {
      if (err.name !== 'AbortError') {
        setMessages(prev => [...prev, { role: 'system', text: `⚠ 连接失败：${err.message}` }])
        setIsRunning(false)
      }
    }
  }

  const handleStop = () => {
    abortRef.current?.abort()
    if (audioCtxRef.current?.state !== 'closed') audioCtxRef.current?.close()
    setIsRunning(false)
    setIsDone(true)
    setActiveRole(null)
  }

  const handleRestart = () => {
    startDuet()
  }

  if (!charA || !charB) return null

  return (
    <div
      className="duet-page"
      style={{ backgroundImage: `url("${activeRole === charB.id ? charB.bg : charA.bg}")` }}
    >
      <div className="duet-bg-overlay" />

      <header className="duet-header">
        <button className="duet-back-btn" onClick={() => { handleStop(); navigate('/select') }}>
          ← 返回选角
        </button>
        <div className="duet-title">
          🎭 {charA.name} × {charB.name}
          {context && <span className="duet-scene-inline">｜{context}</span>}
        </div>
        <div className="duet-header-actions">
          {isRunning && (
            <button className="duet-stop-btn" onClick={handleStop}>⏹ 停止</button>
          )}
          {isDone && (
            <button className="duet-restart-btn" onClick={handleRestart}>↺ 再演一场</button>
          )}
          <button
            className={`duet-music-btn ${muted ? 'duet-music-btn--muted' : ''}`}
            onClick={toggleMute}
            title={muted ? '开启音乐' : '关闭音乐'}
          >
            ♪{muted && <span className="duet-music-slash" />}
          </button>
        </div>
      </header>

      <div className="duet-main">
        {/* 左侧：角色A */}
        <aside className={`duet-side-panel ${activeRole === charA.id ? 'duet-side-panel--active' : activeRole ? 'duet-side-panel--dim' : ''}`}>
          <img className="duet-side-photo" src={charA.photo} alt={charA.name} />
          <div className="duet-side-name">{charA.name}</div>
          {activeRole === charA.id && (
            <div className="duet-sound-wave">
              <span /><span /><span />
            </div>
          )}
          {isRunning && !activeRole && <div className="duet-loading-ring" />}
        </aside>

        {/* 中间：消息流 */}
        <main className="duet-messages">
          {messages.length === 0 && isRunning && (
            <div className="duet-start-hint">
              <div className="duet-loading-ring" />
              <span>即将开演…</span>
            </div>
          )}

          {messages.map((msg, i) =>
            msg.role === 'system' ? (
              <div key={i} className="duet-msg-system">
                <span>{msg.text}</span>
              </div>
            ) : (
              <div
                key={i}
                className={`duet-msg-row ${msg.role === charA.id ? 'duet-msg-row--a' : 'duet-msg-row--b'}`}
              >
                {msg.role === charA.id && (
                  <img className="duet-msg-avatar" src={charA.photo} alt={charA.name} />
                )}
                <div className="duet-bubble">{msg.text}</div>
                {msg.role === charB.id && (
                  <img className="duet-msg-avatar" src={charB.photo} alt={charB.name} />
                )}
              </div>
            )
          )}

          {isDone && messages.length > 0 && (
            <div className="duet-done-hint">— 即兴对话已落幕 —</div>
          )}

          <div ref={messagesEndRef} />
        </main>

        {/* 右侧：角色B */}
        <aside className={`duet-side-panel ${activeRole === charB.id ? 'duet-side-panel--active' : activeRole ? 'duet-side-panel--dim' : ''}`}>
          <img className="duet-side-photo" src={charB.photo} alt={charB.name} />
          <div className="duet-side-name">{charB.name}</div>
          {activeRole === charB.id && (
            <div className="duet-sound-wave">
              <span /><span /><span />
            </div>
          )}
          {isRunning && !activeRole && <div className="duet-loading-ring" />}
        </aside>
      </div>

      <footer className="duet-footer">
        <span className="duet-footer-scene">
          {context ? `场景：${context}` : '场景：两位角色相遇'}
        </span>
        <span className="duet-footer-status">
          {isDone ? '已落幕' : isRunning ? `第 ${round} 轮` : ''}
        </span>
      </footer>
    </div>
  )
}
