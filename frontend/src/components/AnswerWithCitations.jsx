import React, { useState, useRef, useEffect } from 'react'
import { Quote } from 'lucide-react'

/**
 * Parse answer text containing [n] citation refs and render
 * them as interactive superscript badges with hover tooltips.
 */
export default function AnswerWithCitations({ text, citationMap, onCitationClick }) {
  const tooltipRef = useRef(null)
  const [tooltip, setTooltip] = useState(null) // { num, x, y, content }

  // Parse [n] patterns from text
  const parts = parseCitationParts(text)

  // Close tooltip on outside click
  useEffect(() => {
    if (!tooltip) return
    const handleClick = (e) => {
      if (tooltipRef.current && !tooltipRef.current.contains(e.target)) {
        setTooltip(null)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [tooltip])

  return (
    <div className="relative">
      <p className="text-text-primary leading-relaxed whitespace-pre-wrap">
        {parts.map((part, i) => {
          if (part.type === 'text') {
            return <span key={i}>{part.value}</span>
          }
          const num = part.value    // e.g. "1" from "[1]"
          const cite = citationMap?.[num]
          const tooltipContent = cite
            ? `[${num}] Page ${cite.page_number}: "${cite.first_sentence || cite.text?.slice(0, 120)}"`
            : `[${num}] citation not found`

          return (
            <sup
              key={i}
              className="inline-flex items-center justify-center w-5 h-5 mx-0.5 rounded text-xs font-mono font-bold
                         bg-accent-primary/15 text-accent-primary border border-accent-primary/25 cursor-pointer
                         hover:bg-accent-primary/25 hover:scale-110 transition-all align-middle"
              style={{ verticalAlign: 'super', fontSize: '0.65em', lineHeight: 1 }}
              title={tooltipContent}
              onClick={() => {
                if (cite && onCitationClick) {
                  onCitationClick(cite.id)
                }
              }}
              onMouseEnter={(e) => {
                const rect = e.target.getBoundingClientRect()
                const containerRect = e.target.closest('.relative').getBoundingClientRect()
                setTooltip({
                  num,
                  x: rect.left - containerRect.left + rect.width / 2,
                  y: rect.bottom - containerRect.top + 4,
                  content: tooltipContent,
                  cite,
                })
              }}
              onMouseLeave={() => setTooltip(null)}
            >
              {num}
            </sup>
          )
        })}
      </p>

      {/* Hover tooltip */}
      {tooltip && (
        <div
          ref={tooltipRef}
          className="absolute z-50 left-1/2 -translate-x-1/2 w-72 px-3 py-2.5 rounded-xl border border-accent-primary/30
                     bg-bg-card shadow-xl shadow-black/30 pointer-events-none"
          style={{ top: tooltip.y, position: 'absolute' }}
        >
          {/* Arrow */}
          <div className="absolute -top-1.5 left-1/2 -translate-x-1/2 w-3 h-3 rotate-45 border-l border-t border-accent-primary/30
                          bg-bg-card" />
          <div className="flex items-start gap-2">
            <Quote className="w-3.5 h-3.5 text-accent-primary flex-shrink-0 mt-0.5" />
            <div className="min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-mono font-bold text-accent-primary">[{tooltip.num}]</span>
                {tooltip.cite && (
                  <span className="text-xs text-text-muted">Page {tooltip.cite.page_number}</span>
                )}
              </div>
              <p className="text-xs text-text-secondary leading-relaxed italic line-clamp-4">
                {tooltip.content?.replace(/^\[\d+\]\s*/, '')}
              </p>
              {tooltip.cite && (
                <p className="text-xs text-accent-primary mt-1.5 font-medium">Click to jump to source</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

/**
 * Parse text into segments: plain text or citation refs.
 * Handles: [1], [2], [12], etc.
 */
function parseCitationParts(text) {
  if (!text) return [{ type: 'text', value: '' }]
  const parts = []
  // Match [n] where n is one or more digits
  const regex = /\[(\d+)\]/g
  let lastIndex = 0
  let match
  while ((match = regex.exec(text)) !== null) {
    // Text before the citation
    if (match.index > lastIndex) {
      parts.push({ type: 'text', value: text.slice(lastIndex, match.index) })
    }
    // Citation
    parts.push({ type: 'citation', value: match[1] })
    lastIndex = regex.lastIndex
  }
  // Remaining text
  if (lastIndex < text.length) {
    parts.push({ type: 'text', value: text.slice(lastIndex) })
  }
  return parts
}
