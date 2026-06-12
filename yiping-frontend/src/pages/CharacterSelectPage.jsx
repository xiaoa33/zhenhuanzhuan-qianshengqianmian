import { useState, useRef, useContext } from 'react'
import { useNavigate } from 'react-router-dom'
import { MusicContext } from '../App'
import { characters } from '../data/characters'
import './CharacterSelectPage.css'

export default function CharacterSelectPage() {
  const navigate = useNavigate()
  const { muted, toggleMute } = useContext(MusicContext)

  const [userIdentity, setUserIdentity] = useState(null) // 'modern' | 'ancient' | 'duet'
  const [userRole, setUserRole] = useState(null)
  const [targetChar, setTargetChar] = useState(null)
  const [exiting, setExiting] = useState(false)

  // 即兴对话状态
  const [duetCharA, setDuetCharA] = useState(null)
  const [duetCharB, setDuetCharB] = useState(null)
  const [duetContext, setDuetContext] = useState('')
  const [duetStarter, setDuetStarter] = useState('a')

  // Toast：用 { msg, id } 保证每次选择都能重新触发动画
  const [toast, setToast] = useState(null)
  const toastTimerRef = useRef(null)

  const showToast = (msg) => {
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current)
    setToast({ msg, id: Date.now() })
    toastTimerRef.current = setTimeout(() => setToast(null), 2200)
  }

  const handleSetIdentity = (identity) => {
    setUserIdentity(identity)
    if (identity !== 'ancient') setUserRole(null)
    setTargetChar(null)
  }

  // 选对话角色：只高亮，不直接跳转
  const handleSelectTarget = (character) => {
    if (exiting) return
    setTargetChar(character)
    showToast(`已选择：${character.name}`)
  }

  // 确认按钮跳转
  const handleConfirm = () => {
    if (!targetChar || exiting) return
    setExiting(true)
    setTimeout(() => {
      navigate('/chat', {
        state: {
          character: targetChar,
          userIdentity: userIdentity || 'modern',
          userRole: userRole || null,
        },
      })
    }, 400)
  }

  const handleSelectUserRole = (c) => {
    setUserRole(c)
    showToast(`已选择扮演：${c.name}`)
  }

  const handleSelectDuetA = (c) => {
    setDuetCharA(c)
    showToast(`已选择角色A：${c.name}`)
  }

  const handleSelectDuetB = (c) => {
    setDuetCharB(c)
    showToast(`已选择角色B：${c.name}`)
  }

  const handleStartDuet = () => {
    if (!duetCharA || !duetCharB || exiting) return
    setExiting(true)
    setTimeout(() => {
      navigate('/duet', {
        state: {
          charA: duetCharA,
          charB: duetCharB,
          context: duetContext.trim(),
          starter: duetStarter === 'a' ? duetCharA.id : duetCharB.id,
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
        state: { character: random, userIdentity: 'modern', userRole: null },
      })
    }, 400)
  }

  return (
    <div className={`select-page ${exiting ? 'select-page--exit' : ''}`}>
      <div className="select-bg" />
      <div className="select-overlay" />

      {/* Toast 确认气泡 */}
      {toast && (
        <div key={toast.id} className="select-toast">✓ {toast.msg}</div>
      )}

      <div className="select-content">
        <button className="back-btn" onClick={() => navigate('/')}>
          ← 返回主页
        </button>
        <h2 className="select-title">选择你的身份</h2>

        {/* ── 身份选择 ── */}
        <div className="identity-row">
          <button
            className={`identity-card ${userIdentity === 'modern' ? 'identity-card--active' : ''}`}
            onClick={() => handleSetIdentity('modern')}
          >
            <span className="identity-icon">🏛</span>
            <span className="identity-name">现代来客</span>
            <span className="identity-desc">以现代人身份入宫</span>
          </button>

          <button
            className={`identity-card ${userIdentity === 'ancient' ? 'identity-card--active' : ''}`}
            onClick={() => handleSetIdentity('ancient')}
          >
            <span className="identity-icon">👘</span>
            <span className="identity-name">宫廷中人</span>
            <span className="identity-desc">扮演剧中角色入宫</span>
          </button>

          <button
            className={`identity-card ${userIdentity === 'duet' ? 'identity-card--active' : ''}`}
            onClick={() => handleSetIdentity('duet')}
          >
            <span className="identity-icon">🎭</span>
            <span className="identity-name">即兴对话</span>
            <span className="identity-desc">让两位角色自动演出</span>
          </button>
        </div>

        {/* ── 即兴对话配置区 ── */}
        {userIdentity === 'duet' && (
          <div className="duet-section">
            <div className="duet-ab-row">
              <div className="duet-char-select">
                <p className="section-label">
                  角色 A
                  {duetCharA && <span className="duet-selected-hint">：{duetCharA.name}</span>}
                </p>
                <div className="char-grid char-grid--compact">
                  {characters.map((c, i) => (
                    <button
                      key={c.id}
                      className={`char-card ${duetCharA?.id === c.id ? 'char-card--selected' : ''}`}
                      style={{ animationDelay: `${i * 40}ms` }}
                      onClick={() => handleSelectDuetA(c)}
                    >
                      {duetCharA?.id === c.id && <span className="char-check">✓</span>}
                      <img className="char-photo" src={c.photo} alt={c.name} />
                      <span className="char-name">{c.name}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div className="duet-vs-divider">VS</div>

              <div className="duet-char-select">
                <p className="section-label">
                  角色 B
                  {duetCharB && <span className="duet-selected-hint">：{duetCharB.name}</span>}
                </p>
                <div className="char-grid char-grid--compact">
                  {characters.map((c, i) => (
                    <button
                      key={c.id}
                      className={`char-card ${duetCharB?.id === c.id ? 'char-card--selected' : ''}`}
                      style={{ animationDelay: `${i * 40}ms` }}
                      onClick={() => handleSelectDuetB(c)}
                    >
                      {duetCharB?.id === c.id && <span className="char-check">✓</span>}
                      <img className="char-photo" src={c.photo} alt={c.name} />
                      <span className="char-name">{c.name}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="duet-scene-row">
              <p className="section-label">场景描述（可选）</p>
              <textarea
                className="duet-context-input"
                value={duetContext}
                onChange={e => setDuetContext(e.target.value)}
                placeholder="描述两位角色相遇的场景，如：御花园偶遇，恰逢落雪"
                rows={2}
              />
            </div>

            <div className="duet-starter-row">
              <span className="section-label" style={{ margin: 0 }}>先开口</span>
              <button
                className={`duet-chip ${duetStarter === 'a' ? 'duet-chip--active' : ''}`}
                onClick={() => setDuetStarter('a')}
              >
                {duetCharA ? duetCharA.name : '角色A'}
              </button>
              <button
                className={`duet-chip ${duetStarter === 'b' ? 'duet-chip--active' : ''}`}
                onClick={() => setDuetStarter('b')}
              >
                {duetCharB ? duetCharB.name : '角色B'}
              </button>
            </div>

            <button
              className="duet-start-btn"
              onClick={handleStartDuet}
              disabled={!duetCharA || !duetCharB}
            >
              🎭 开始即兴对话
            </button>
          </div>
        )}

        {/* ── 宫廷中人：左右双列布局 ── */}
        {userIdentity === 'ancient' && (
          <div className="ancient-layout">
            <div className="ancient-col">
              <p className="section-label">请选择你扮演的角色</p>
              <div className="char-grid char-grid--compact">
                {characters.map((c, i) => (
                  <button
                    key={c.id}
                    className={`char-card ${userRole?.id === c.id ? 'char-card--selected' : ''}`}
                    style={{ animationDelay: `${i * 50}ms` }}
                    onClick={() => handleSelectUserRole(c)}
                  >
                    {userRole?.id === c.id && <span className="char-check">✓</span>}
                    <img className="char-photo" src={c.photo} alt={c.name} />
                    <span className="char-name">{c.name}</span>
                  </button>
                ))}
              </div>
            </div>

            <div className="ancient-divider" />

            <div className="ancient-col">
              <p className="section-label">
                选择你想对话的角色
                {targetChar && <span className="duet-selected-hint">：{targetChar.name}</span>}
              </p>
              <div className="char-grid char-grid--compact">
                {characters.map((c, i) => (
                  <button
                    key={c.id}
                    className={`char-card ${targetChar?.id === c.id ? 'char-card--selected' : ''}`}
                    style={{ animationDelay: `${i * 50}ms` }}
                    onClick={() => handleSelectTarget(c)}
                  >
                    {targetChar?.id === c.id && <span className="char-check">✓</span>}
                    <img className="char-photo" src={c.photo} alt={c.name} />
                    <span className="char-name">{c.name}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ── 现代来客（及未选身份）：全宽对话角色选择 ── */}
        {(userIdentity === 'modern' || userIdentity === null) && (
          <div className="role-section">
            <p className="section-label">
              选择你想对话的角色
              {targetChar && <span className="duet-selected-hint">：{targetChar.name}</span>}
            </p>
            <div className="char-grid">
              {characters.map((c, i) => (
                <button
                  key={c.id}
                  className={`char-card ${targetChar?.id === c.id ? 'char-card--selected' : ''}`}
                  style={{ animationDelay: `${i * 100}ms` }}
                  onClick={() => handleSelectTarget(c)}
                >
                  {targetChar?.id === c.id && <span className="char-check">✓</span>}
                  <img className="char-photo" src={c.photo} alt={c.name} />
                  <span className="char-name">{c.name}</span>
                  <span className="char-quote">「{c.quote}」</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* ── 确认行（现代来客 / 宫廷中人） ── */}
        {userIdentity !== 'duet' && (
          <div className="confirm-row">
            {targetChar && (
              <button className="confirm-btn" onClick={handleConfirm}>
                开始对话
              </button>
            )}
            <button className="skip-link" onClick={handleSkip}>
              不选角色，直接对话
            </button>
          </div>
        )}
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
