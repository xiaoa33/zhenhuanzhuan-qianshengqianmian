import { useRef, useState, useEffect } from 'react'
import html2canvas from 'html2canvas'
import { getSummary } from '../api'
import './SummaryCard.css'

export default function SummaryCard({ character, messages, onClose, onRestart }) {
  const cardRef = useRef(null)
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  const rounds = messages.filter(m => m.role === 'user').length

  useEffect(() => {
    getSummary(character.id, messages)
      .then(data => setSummary(data))
      .catch(() =>
        setSummary({
          attitude: '不置可否',
          comment: '此次对话已载入宫廷密录',
          rounds,
        })
      )
      .finally(() => setLoading(false))
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleSave = async () => {
    if (!cardRef.current || saving) return
    setSaving(true)
    try {
      const canvas = await html2canvas(cardRef.current, {
        backgroundColor: '#140f0a',
        scale: 2,
        useCORS: true,
      })
      const link = document.createElement('a')
      link.download = `今日宫廷密录_${character.name}.png`
      link.href = canvas.toDataURL('image/png')
      link.click()
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="summary-backdrop" onClick={onClose}>
      <div
        className="summary-modal"
        onClick={e => e.stopPropagation()}
      >
        <div className="summary-card" ref={cardRef}>
          <h3 className="summary-title">今日宫廷密录</h3>
          <div className="summary-divider" />

          <div className="summary-avatar-row">
            <img
              className="summary-avatar"
              src={character.photo}
              alt={character.name}
            />
            <span className="summary-char-name">{character.name}</span>
          </div>

          <p className="summary-rounds">共交谈 {summary?.rounds ?? rounds} 句</p>

          {loading ? (
            <div className="summary-loading">
              <span className="dot" /><span className="dot" /><span className="dot" />
            </div>
          ) : (
            <>
              <p className="summary-attitude">
                {character.name}今日对你：
                <span className="summary-attitude-value">{summary.attitude}</span>
              </p>
              <p className="summary-comment">「{summary.comment}」</p>
            </>
          )}

          <div className="summary-divider" />
        </div>

        <div className="summary-actions">
          <button
            className="summary-btn summary-btn--save"
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? '生成中…' : '保存图片'}
          </button>
          <button className="summary-btn summary-btn--restart" onClick={onRestart}>
            再聊一次
          </button>
        </div>
      </div>
    </div>
  )
}
