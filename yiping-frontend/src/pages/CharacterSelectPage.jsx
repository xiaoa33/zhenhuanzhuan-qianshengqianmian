import { useState, useContext } from 'react'
import { useNavigate } from 'react-router-dom'
import { MusicContext } from '../App'
import { characters } from '../data/characters'
import './CharacterSelectPage.css'

export default function CharacterSelectPage() {
  const navigate = useNavigate()
  const { muted, toggleMute } = useContext(MusicContext)

  const [userIdentity, setUserIdentity] = useState(null) // 'modern' | 'ancient'
  const [userRole, setUserRole] = useState(null)          // character object or null
  const [exiting, setExiting] = useState(false)

  const handleSelectTarget = (character) => {
    if (exiting) return
    setExiting(true)
    setTimeout(() => {
      navigate('/chat', {
        state: {
          character,
          userIdentity: userIdentity || 'modern',
          userRole: userRole || null,
        },
      })
    }, 400)
  }

  const handleSkip = () => {
    if (exiting) return
    const random = characters[Math.floor(Math.random() * characters.length)]
    setExiting(true)
    setTimeout(() => {
      navigate('/chat', {
        state: {
          character: random,
          userIdentity: 'modern',
          userRole: null,
        },
      })
    }, 400)
  }

  return (
    <div className={`select-page ${exiting ? 'select-page--exit' : ''}`}>
      <div className="select-bg" />
      <div className="select-overlay" />

      <div className="select-content">
        <button className="back-btn" onClick={() => navigate('/')}>
          ← 返回主页
        </button>
        <h2 className="select-title">选择你的身份</h2>

        {/* ── 身份选择 ── */}
        <div className="identity-row">
          <button
            className={`identity-card ${userIdentity === 'modern' ? 'identity-card--active' : ''}`}
            onClick={() => { setUserIdentity('modern'); setUserRole(null) }}
          >
            <span className="identity-icon">🏛</span>
            <span className="identity-name">现代来客</span>
            <span className="identity-desc">以现代人身份入宫</span>
          </button>

          <button
            className={`identity-card ${userIdentity === 'ancient' ? 'identity-card--active' : ''}`}
            onClick={() => setUserIdentity('ancient')}
          >
            <span className="identity-icon">👘</span>
            <span className="identity-name">宫廷中人</span>
            <span className="identity-desc">扮演剧中角色入宫</span>
          </button>
        </div>

        {/* ── 扮演者选择（仅宫廷中人展开） ── */}
        {userIdentity === 'ancient' && (
          <div className="role-section">
            <p className="section-label">请选择你扮演的角色</p>
            <div className="char-grid char-grid--role">
              {characters.map((c, i) => (
                <button
                  key={c.id}
                  className={`char-card ${userRole?.id === c.id ? 'char-card--selected' : ''}`}
                  style={{ animationDelay: `${i * 60}ms` }}
                  onClick={() => setUserRole(c)}
                >
                  <img className="char-photo" src={c.photo} alt={c.name} />
                  <span className="char-name">{c.name}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* ── 对话角色选择 ── */}
        <div className="role-section">
          <p className="section-label">选择你想对话的角色</p>
          <div className="char-grid">
            {characters.map((c, i) => (
              <button
                key={c.id}
                className="char-card"
                style={{ animationDelay: `${i * 100}ms` }}
                onClick={() => handleSelectTarget(c)}
              >
                <img className="char-photo" src={c.photo} alt={c.name} />
                <span className="char-name">{c.name}</span>
                <span className="char-quote">「{c.quote}」</span>
              </button>
            ))}
          </div>
        </div>

        <button className="skip-link" onClick={handleSkip}>
          不选角色，直接对话
        </button>
      </div>

      <button
        className={`music-btn ${muted ? 'music-btn--muted' : ''}`}
        onClick={toggleMute}
        title={muted ? '开启音乐' : '关闭音乐'}
      >
        ♪
        {muted && <span className="music-slash" />}
      </button>
    </div>
  )
}
