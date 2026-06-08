import { useContext } from 'react'
import { useNavigate } from 'react-router-dom'
import { MusicContext } from '../App'
import './HomePage.css'

export default function HomePage() {
  const navigate = useNavigate()
  const { muted, toggleMute, tryPlay } = useContext(MusicContext)

  const handleEnter = () => {
    tryPlay()
    navigate('/select')
  }

  return (
    <div className="home-page">
      <div className="home-bg" />
      <div className="home-overlay" />

      <div className="home-content">
        <h1 className="home-title">甄嬛传·千声千面</h1>
        <p className="home-subtitle">入宫廷，闻千声</p>
        <button className="home-enter-btn" onClick={handleEnter}>
          进入宫廷
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
