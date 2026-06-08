import { createContext, useRef, useState } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import HomePage from './pages/HomePage'
import CharacterSelectPage from './pages/CharacterSelectPage'
import ChatPage from './pages/ChatPage'

export const MusicContext = createContext(null)

export default function App() {
  const audioRef = useRef(null)
  const [muted, setMuted] = useState(false)

  const toggleMute = () => {
    if (!audioRef.current) return
    const next = !muted
    audioRef.current.muted = next
    setMuted(next)
  }

  const tryPlay = () => {
    if (audioRef.current) {
      audioRef.current.volume = 0.4
      audioRef.current.play().catch(() => {})
    }
  }

  return (
    <MusicContext.Provider value={{ muted, toggleMute, tryPlay }}>
      <audio
        ref={audioRef}
        src="/resource/长相思（甄嬛传背景音乐）.mp3"
        loop
        autoPlay
        onCanPlay={tryPlay}
      />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/select" element={<CharacterSelectPage />} />
          <Route path="/chat" element={<ChatPage />} />
        </Routes>
      </BrowserRouter>
    </MusicContext.Provider>
  )
}
