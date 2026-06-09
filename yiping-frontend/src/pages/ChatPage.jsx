import { useState, useRef, useEffect, useContext, useCallback } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { MusicContext } from '../App'
import SummaryCard from '../components/SummaryCard'
import { sendMessage, synthesizeAudio, generateDigitalHuman, transcribeAudio } from '../api'
import './ChatPage.css'

const QUICK_PHRASES = ['臣妾做不到啊', '贱人就是矫情', '愿得一心人', '皇上圣安']
const EMOTION_OPTIONS = ['自动', '喜悦', '愤怒', '悲伤', '平静']
const DEFAULT_TTS_ENGINE = import.meta.env.VITE_TTS_ENGINE || 'gpt_sovits'
const TTS_ENGINE_OPTIONS = [
  { id: 'gpt_sovits', label: 'GPT-SoVITS' },
  { id: 'cosyvoice', label: 'CosyVoice' },
]

function ttsTextKey(engine) {
  return engine === 'gpt-sovits' ? 'gpt_sovits' : engine
}

export default function ChatPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const { muted, toggleMute } = useContext(MusicContext)

  const { character, userIdentity, userRole } = location.state || {}

  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isPlaying, setIsPlaying] = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const [isTranscribing, setIsTranscribing] = useState(false)
  const [videoUrl, setVideoUrl] = useState(null)
  const [emotion, setEmotion] = useState('平静')
  const [preferredEmotion, setPreferredEmotion] = useState('自动')
  const [ttsEngine, setTtsEngine] = useState(DEFAULT_TTS_ENGINE)
  const [showSummary, setShowSummary] = useState(false)

  const messagesEndRef = useRef(null)
  const chatAudioRef = useRef(null)
  const mediaRecorderRef = useRef(null)
  const audioChunksRef = useRef([])

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
    if (!input.trim() || isLoading || isTranscribing) return
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
        userText,
        preferredEmotion === '自动' ? null : preferredEmotion
      )
      const replyText = chatRes.text
      const replyEmotion = chatRes.emotion || '平静'
      const ttsTexts = chatRes.tts_texts || {}
      const ttsText = ttsTexts[ttsTextKey(ttsEngine)] || replyText

      setMessages(prev => [...prev, { role: 'character', text: replyText, emotion: replyEmotion }])
      setEmotion(replyEmotion)

      // 2. 语音合成
      try {
        const audioRes = await synthesizeAudio(character.id, ttsText, replyEmotion, ttsEngine)
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
      } catch (err) {
        // 语音合成失败时仍展示文字回复
        setMessages(prev => [
          ...prev,
          { role: 'system', text: `⚠ 语音合成失败：${err.message}` },
        ])
      }
    } catch (err) {
      setMessages(prev => [
        ...prev,
        { role: 'system', text: `⚠ 与后端通信失败：${err.message}` },
      ])
    } finally {
      setIsLoading(false)
    }
  }, [input, isLoading, isTranscribing, character, userIdentity, userRole, messages, preferredEmotion, ttsEngine])

  const handleRecordToggle = useCallback(async () => {
    if (isLoading || isTranscribing) return

    if (isRecording) {
      mediaRecorderRef.current?.stop()
      return
    }

    if (!navigator.mediaDevices?.getUserMedia) {
      setMessages(prev => [
        ...prev,
        { role: 'system', text: '⚠ 当前浏览器不支持录音' },
      ])
      return
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      audioChunksRef.current = []

      recorder.ondataavailable = (event) => {
        if (event.data?.size > 0) audioChunksRef.current.push(event.data)
      }

      recorder.onstop = async () => {
        setIsRecording(false)
        stream.getTracks().forEach(track => track.stop())

        const blob = new Blob(audioChunksRef.current, { type: recorder.mimeType || 'audio/webm' })
        audioChunksRef.current = []
        if (!blob.size) return

        setIsTranscribing(true)
        try {
          const result = await transcribeAudio(blob)
          if (result.text?.trim()) {
            setInput(result.text.trim())
          } else {
            setMessages(prev => [
              ...prev,
              { role: 'system', text: '⚠ 未识别到有效语音' },
            ])
          }
        } catch {
          setMessages(prev => [
            ...prev,
            { role: 'system', text: '⚠ 语音识别失败，请检查 ASR 服务' },
          ])
        } finally {
          setIsTranscribing(false)
        }
      }

      mediaRecorderRef.current = recorder
      recorder.start()
      setIsRecording(true)
    } catch {
      setMessages(prev => [
        ...prev,
        { role: 'system', text: '⚠ 无法开启麦克风，请检查浏览器权限' },
      ])
    }
  }, [isLoading, isRecording, isTranscribing])

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
          <div className="emotion-picker" aria-label="情绪选择">
            <span className="emotion-picker-label">情绪</span>
            {EMOTION_OPTIONS.map(item => (
              <button
                key={item}
                className={`emotion-chip ${preferredEmotion === item ? 'emotion-chip--active' : ''}`}
                onClick={() => setPreferredEmotion(item)}
                disabled={isLoading || isTranscribing}
              >
                {item}
              </button>
            ))}
          </div>
          <div className="model-picker" aria-label="语音模型选择">
            <span className="emotion-picker-label">模型</span>
            {TTS_ENGINE_OPTIONS.map(item => (
              <button
                key={item.id}
                className={`emotion-chip ${ttsEngine === item.id ? 'emotion-chip--active' : ''}`}
                onClick={() => setTtsEngine(item.id)}
                disabled={isLoading || isTranscribing}
              >
                {item.label}
              </button>
            ))}
          </div>
          <div className="input-row">
            <button
              className={`record-btn ${isRecording ? 'record-btn--active' : ''}`}
              onClick={handleRecordToggle}
              disabled={isLoading || isTranscribing}
              title={isRecording ? '停止录音' : '开始录音'}
            >
              {isRecording ? '■' : '●'}
            </button>
            <input
              className="chat-input"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={isRecording ? '正在听…' : isTranscribing ? '识别中…' : '请说话…'}
              disabled={isLoading || isTranscribing}
            />
            <button
              className="send-btn"
              onClick={handleSend}
              disabled={isLoading || isTranscribing || !input.trim()}
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
