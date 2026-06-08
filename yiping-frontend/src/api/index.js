const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

/**
 * POST /chat
 * @param {string} characterId - 对话角色 ID
 * @param {string} userIdentity - 'modern' | 'ancient'
 * @param {string|null} userRoleId - 用户扮演的角色 ID（仅 ancient 时有值）
 * @param {string|null} userRoleName - 用户扮演的角色名（仅 ancient 时有值，供 LLM 直接使用）
 * @param {Array} history - 历史消息 [{role, text}]
 * @param {string} userInput - 用户本轮输入
 * @returns {{ text: string, emotion: string }}
 */
export async function sendMessage(characterId, userIdentity, userRoleId, userRoleName, history, userInput) {
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
    }),
  })
  if (!res.ok) throw new Error(`Chat failed: ${res.status}`)
  return res.json()
}

/**
 * POST /synthesize
 * @param {string} characterId
 * @param {string} text
 * @param {string} emotion
 * @returns {{ audio_url: string }}
 */
export async function synthesizeAudio(characterId, text, emotion) {
  const res = await fetch(`${BASE_URL}/synthesize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ character_id: characterId, text, emotion }),
  })
  if (!res.ok) throw new Error(`Synthesize failed: ${res.status}`)
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
  if (!res.ok) throw new Error(`Digital human failed: ${res.status}`)
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
  if (!res.ok) throw new Error(`Summary failed: ${res.status}`)
  return res.json()
}
