/**
 * lib/textUtils.ts
 * Text cleaning utilities shared across the app.
 */

// ── Query cleaning ─────────────────────────────────────────────────────────────

/**
 * Clean pasted PDF text before sending as a search query.
 * Removes PDF escape chars, OCR artifacts, excess whitespace.
 */
export function cleanPastedText(raw: string): string {
  return raw
    // Remove PDF escape sequences like \026 \027 \x00 etc.
    .replace(/\\[0-9]{2,3}/g, ' ')
    // eslint-disable-next-line no-control-regex
    .replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, ' ')
    // Remove common PDF artifacts
    .replace(/\uFFFD/g, ' ')   // replacement character
    .replace(/\f/g, ' ')       // form feed
    .replace(/\r\n/g, '\n')    // normalize line endings
    .replace(/\r/g, '\n')
    // Collapse multiple spaces/newlines
    .replace(/[ \t]{2,}/g, ' ')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

// ── TTS markdown stripper ──────────────────────────────────────────────────────

/**
 * Strip Markdown formatting before sending text to TTS.
 * So "**bold**" is spoken as "bold", not "asterisk asterisk bold asterisk asterisk".
 */
export function stripMarkdownForSpeech(text: string): string {
  return text
    .replace(/```[\s\S]*?```/g, '')
    .replace(/`[^`]+`/g, '')
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/\*([^*]+)\*/g, '$1')
    .replace(/__([^_]+)__/g, '$1')
    .replace(/_([^_]+)_/g, '$1')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/^[-*_]{3,}\s*$/gm, '')
    .replace(/^>\s+/gm, '')
    .replace(/^[\s]*[-*+]\s+/gm, ' ')
    .replace(/^[\s]*\d+\.\s+/gm, ' ')
    .replace(/\|[-:]+\|/g, '')
    .replace(/\|/g, ' ')
    .replace(/\n{2,}/g, '. ')
    .replace(/\n/g, ' ')
    .replace(/\s{2,}/g, ' ')
    .trim()
}
