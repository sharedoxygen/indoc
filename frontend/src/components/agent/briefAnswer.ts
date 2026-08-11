/** Normalize agent brief text so the reader can render structured markdown. */

const UUID_RE = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gi
const DOC_ID_INLINE_RE = /\(\s*document\s*id\s*=\s*([0-9a-f-]{36})\s*\)/gi
const NUMBERED_BOLD_RE = /(\d+)\.\s+(\*\*[^*]+\*\*)/g

export function extractDocumentIds(answer: string): string[] {
  const seen = new Set<string>()
  const ids: string[] = []
  for (const match of answer.matchAll(UUID_RE)) {
    const id = match[0].toLowerCase()
    if (!seen.has(id)) {
      seen.add(id)
      ids.push(id)
    }
  }
  return ids
}

/**
 * Turn wall-of-prose agent answers into markdown the Brief reader can layout.
 * Leaves already-structured markdown alone.
 */
export function formatBriefAnswer(raw: string): string {
  let text = (raw || '').trim()
  if (!text) return text

  text = text.replace(DOC_ID_INLINE_RE, '(`$1`)')

  const hasBlockStructure =
    /^#{1,3}\s/m.test(text) ||
    /^\s*[-*]\s/m.test(text) ||
    /\n\s*\d+\.\s/.test(text)
  if (hasBlockStructure) return text

  const matches = [...text.matchAll(NUMBERED_BOLD_RE)]
  if (matches.length < 2) return text

  const firstIdx = matches[0].index ?? 0
  const intro = text.slice(0, firstIdx).replace(/:\s*$/, '').trim()

  const items: { title: string; body: string }[] = []
  for (let i = 0; i < matches.length; i++) {
    const m = matches[i]
    const start = (m.index ?? 0) + m[0].length
    const end = i + 1 < matches.length ? (matches[i + 1].index ?? text.length) : text.length
    items.push({
      title: m[2],
      body: text.slice(start, end).trim(),
    })
  }

  let outro = ''
  const last = items[items.length - 1]
  const outroMatch = last.body.match(/^(.*?[.!?])\s+((?:These|This|Overall|In summary|Together)\b[\s\S]+)$/i)
  if (outroMatch) {
    last.body = outroMatch[1].trim()
    outro = outroMatch[2].trim()
  }

  const list = items
    .map(({ title, body }, idx) => {
      const cleaned = body.replace(/^[,:\s—–-]+/, '').trim()
      return `${idx + 1}. ${title}${cleaned ? ` — ${cleaned}` : ''}`
    })
    .join('\n')

  return [intro ? `${intro}:` : '', list, outro].filter(Boolean).join('\n\n')
}
