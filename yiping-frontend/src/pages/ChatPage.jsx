import { useState, useRef, useEffect, useContext, useCallback } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { MusicContext } from '../App'
import SummaryCard from '../components/SummaryCard'
import { sendMessage, synthesizeAudio, generateDigitalHuman } from '../api'
import './ChatPage.css'

const QUICK_PHRASES = ['臣妾做不到啊', '贱人就是矫情', '愿得一心人', '皇上圣安']

export default function ChatPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const { muted, toggleMute } = useContext(MusicContext)

  const { character, userIdentity, userRole } = location.state || {}

  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isPlaying, setIsPlaying] = useState(false)
  const [videoUrl, setVideoUrl] = useState(null)
  const [emotion, setEmotion] = useState('平静')
  const [showSummary, setShowSummary] = useState(false)

  const messagesEndRef = useRef(null)
  const chatAudioRef = useRef(null)

  useEffect(() => {
    if (!character) navigate('/')
  }, [character, navigate])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  // 情绪效果持续 2.5s 后恢复
  useEffect(() => {
    if (emotion === '平静') return
    const t = setTimeout(() => setEmotion('平静'), 2500)
    return () => clearTimeout(t)
  }, [emotion])

  const handleSend = useCallback(async () => {
    if (!input.trim() || isLoading) return
    const userText = input.trim()
    setInput('')

    setMessages(prev => [...prev, { role: 'user', text: userText }])
    setIsLoading(true)

    try {
      // 1. LLM 对话
      const chatRes = await sendMessage(
        character.id,
        userIdentity || 'modern',
        userRole?.id || null,
        userRole?.name || null,
        messages,
        userText
      )
      const replyText = chatRes.text
      const replyEmotion = chatRes.emotion || '平静'

      setMessages(prev => [...prev, { role: 'character', text: replyText, emotion: replyEmotion }])
      setEmotion(replyEmotion)

      // 2. 语音合成
      try {
        const audioRes = await synthesizeAudio(character.id, replyText, replyEmotion)
        if (audioRes.audio_url && chatAudioRef.current) {
          chatAudioRef.current.src = audioRes.audio_url
          chatAudioRef.current.play()
          setIsPlaying(true)
          chatAudioRef.current.onended = () => setIsPlaying(false)

          // 3. 数字人视频（异步，不阻塞主流程）
          generateDigitalHuman(character.id, audioRes.audio_url)
            .then(videoRes => {
              if (videoRes.video_url) setVideoUrl(videoRes.video_url)
            })
            .catch(() => {})
        }
      } catch {
        // 语音合成失败时仍展示文字回复
      }
    } catch {
      setMessages(prev => [
        ...prev,
        { role: 'system', text: '⚠ 与后端通信失败，请检查服务是否已启动' },
      ])
    } finally {
      setIsLoading(false)
    }
  }, [input, isLoading, character, userIdentity, userRole, messages])

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const emotionClass =
    emotion === '愤怒' ? 'emotion-angry'
    : emotion === '悲伤' ? 'emotion-sad'
    : emotion === '喜悦' ? 'emotion-happy'
    : ''

  if (!character) return null

  return (
    <div
      className="chat-page"
      style={{ backgroundImage: `url("${character.bg}")` }}
    >
      <div className="chat-bg-overlay" />

      <button className="back-btn" onClick={() => navigate('/select')}>
        ← 返回选角
      </button>

      {/* 左侧：数字人区 */}
      <aside className="digital-panel">
        {videoUrl ? (
          <video
            className="char-media"
            src={videoUrl}
            autoPlay
            onEnded={() => setVideoUrl(null)}
          />
        ) : (
          <img className="char-media" src={character.photo} alt={character.name} />
        )}

        <div className="char-name-label">{character.name}</div>

        {isPlaying && (
          <div className="sound-wave">
            <span /><span /><span />
          </div>
        )}

        {isLoading && !isPlaying && (
          <div className="loading-ring" />
        )}
      </aside>

      {/* 右侧：对话区 */}
      <main className={`chat-panel ${emotionClass}`}>
        <header className="chat-header">
          <span className="chat-with-label">
            与 {character.name} 对话中
            {userRole && (
              <span className="user-role-hint">｜你正扮演：{userRole.name}</span>
            )}
          </span>
          <div className="chat-header-right">
            <button
              className={`music-btn-sm ${muted ? 'music-btn-sm--muted' : ''}`}
              onClick={toggleMute}
              title={muted ? '开启音乐' : '关闭音乐'}
            >
              ♪{muted && <span className="music-slash-sm" />}
            </button>
            <button className="end-btn" onClick={() => setShowSummary(true)}>
              结束对话
            </button>
          </div>
        </header>

        <div className="messages-area">
          {messages.length === 0 && (
            <p className="messages-empty">与 {character.name} 开启对话吧</p>
          )}

          {messages.map((msg, i) => (
            <div
              key={i}
              className={`msg-row msg-row--${msg.role}`}
            >
              {msg.role === 'character' && (
                <img className="msg-avatar" src={character.photo} alt={character.name} />
              )}
              {msg.role === 'user' && userRole && (
                <img className="msg-avatar" src={userRole.photo} alt={userRole.name} />
              )}
              <div className={`bubble bubble--${msg.role}`}>
                {msg.text}
              </div>
            </div>
          ))}

          {isLoading && (
            <div className="msg-row msg-row--character">
              <img className="msg-avatar" src={character.photo} alt={character.name} />
              <div className="bubble bubble--character bubble--loading">
                <span className="dot" />
                <span className="dot" />
                <span className="dot" />
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <div className="input-area">
          <div className="quick-phrases">
            {QUICK_PHRASES.map(p => (
              <button key={p} className="quick-btn" onClick={() => setInput(p)}>
                {p}
              </button>
            ))}
          </div>
          <div className="input-row">
            <input
              className="chat-input"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="请说话…"
              disabled={isLoading}
            />
            <button
              className="send-btn"
              onClick={handleSend}
              disabled={isLoading || !input.trim()}
            >
              传话
            </button>
          </div>
        </div>
      </main>

      <audio ref={chatAudioRef} />

      {showSummary && (
        <SummaryCard
          character={character}
          messages={messages}
          onClose={() => setShowSummary(false)}
          onRestart={() => {
            setShowSummary(false)
            setMessages([])
            setVideoUrl(null)
            setEmotion('平静')
          }}
        />
      )}
    </div>
  )
}
