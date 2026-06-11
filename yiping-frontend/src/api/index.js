const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

async function throwApiError(res, fallback) {
  let detail = fallback
  try {
    const data = await res.json()
    detail = data.detail || data.message || detail
  } catch {
    detail = `${fallback}: ${res.status}`
  }
  throw new Error(detail)
}

/**
 * POST /chat
 * @param {string} characterId - 对话角色 ID
 * @param {string} userIdentity - 'modern' | 'ancient'
 * @param {string|null} userRoleId - 用户扮演的角色 ID（仅 ancient 时有值）
 * @param {string|null} userRoleName - 用户扮演的角色名（仅 ancient 时有值，供 LLM 直接使用）
 * @param {Array} history - 历史消息 [{role, text}]
 * @param {string} userInput - 用户本轮输入
 * @param {string|null} preferredEmotion - 手动指定情绪，null 表示自动
 * @returns {{ text: string, emotion: string, tts_texts?: { cosyvoice?: string, gpt_sovits?: string } }}
 */
export async function sendMessage(characterId, userIdentity, userRoleId, userRoleName, history, userInput, preferredEmotion = null) {
  const res = await fetch(`${BASE_URL}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      character_id: characterId,
      user_identity: userIdentity,
      user_role_id: userRoleId,
      user_role_name: userRoleName,
      history: history.map(m => ({ role: m.role, text: m.text })),
      user_input: userInput,
      preferred_emotion: preferredEmotion,
    }),
  })
  if (!res.ok) await throwApiError(res, `Chat failed: ${res.status}`)
  return res.json()
}

/**
 * POST /synthesize
 * @param {string} characterId
 * @param {string} text
 * @param {string} emotion
 * @param {string} engine
 * @returns {{ audio_url: string }}
 */
export async function synthesizeAudio(characterId, text, emotion, engine) {
  const res = await fetch(`${BASE_URL}/synthesize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ character_id: characterId, text, emotion, engine }),
  })
  if (!res.ok) await throwApiError(res, `Synthesize failed: ${res.status}`)
  return res.json()
}

/**
 * POST /synthesize/stream — SSE 流式音频，逐块回调（仅 CosyVoice）
 * @param {function} onChunk - 每收到一个音频块回调 ({i, audio, dur})
 * @param {AbortSignal} [signal] - 取消信号
 */
export async function synthesizeAudioStream(characterId, text, emotion, onChunk, signal) {
  const resp = await fetch(`${BASE_URL}/synthesize/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ character_id: characterId, text, emotion, engine: 'cosyvoice' }),
    signal,
  })
  if (!resp.ok) throw new Error(`Stream failed: ${resp.status}`)

  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buf = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buf += decoder.decode(value, { stream: true })
    const lines = buf.split('\n')
    buf = lines.pop() || ''

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const chunk = JSON.parse(line.slice(6))
        if (chunk.audio) onChunk(chunk)
      } else if (line.startsWith('event: done')) {
        return  // 流结束
      }
    }
  }
}

/**
 * POST /asr
 * @param {Blob} audioBlob - Browser recording blob
 * @returns {{ text: string, language?: string, confidence?: number|null }}
 */
export async function transcribeAudio(audioBlob) {
  const form = new FormData()
  form.append('audio', audioBlob, 'recording.webm')
  const res = await fetch(`${BASE_URL}/asr`, {
    method: 'POST',
    body: form,
  })
  if (!res.ok) await throwApiError(res, `ASR failed: ${res.status}`)
  return res.json()
}

/**
 * POST /digital-human
 * @param {string} characterId
 * @param {string} audioUrl
 * @returns {{ video_url: string }}
 */
export async function generateDigitalHuman(characterId, audioUrl) {
  const res = await fetch(`${BASE_URL}/digital-human`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ character_id: characterId, audio_url: audioUrl }),
  })
  if (!res.ok) await throwApiError(res, `Digital human failed: ${res.status}`)
  return res.json()
}

/**
 * POST /summary
 * @param {string} characterId
 * @param {Array} messages - 完整对话记录
 * @returns {{ attitude: string, comment: string, rounds: number }}
 */
export async function getSummary(characterId, messages) {
  const res = await fetch(`${BASE_URL}/summary`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      character_id: characterId,
      messages: messages.map(m => ({ role: m.role, text: m.text })),
    }),
  })
  if (!res.ok) await throwApiError(res, `Summary failed: ${res.status}`)
  return res.json()
}
