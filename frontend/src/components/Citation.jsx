import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

const TAG_STYLES = {
  GRAPH: {
    bg: 'rgba(194,24,91,0.1)',
    border: 'rgba(194,24,91,0.3)',
    pill: 'rgba(194,24,91,0.18)',
    text: '#b0004a',
    label: 'GRAPH',
  },
  VECTOR: {
    bg: 'rgba(77,182,172,0.1)',
    border: 'rgba(77,182,172,0.28)',
    pill: 'rgba(77,182,172,0.18)',
    text: '#00796b',
    label: 'VECTOR',
  },
}

export default function Citation({ citation, index }) {
  const [open, setOpen] = useState(false)
  const type = citation.type?.toUpperCase() === 'GRAPH' ? 'GRAPH' : 'VECTOR'
  const style = TAG_STYLES[type]
  const offset = (index % 3) * 6

  return (
    <motion.div
      className="citation-item"
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.06, type: 'spring', stiffness: 180, damping: 20 }}
      style={{ marginLeft: offset, marginBottom: index % 2 === 0 ? 10 : 14 }}
    >
      <div
        className="rounded-lg p-3 cursor-pointer transition-all"
        style={{
          background: style.bg,
          border: `1px solid ${style.border}`,
        }}
        onClick={() => setOpen(o => !o)}
      >
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span
              className="text-[9px] font-mono font-semibold px-1.5 py-0.5 rounded"
              style={{ background: style.pill, color: style.text }}
            >
              {style.label}
            </span>
            <span className="text-xs font-mono truncate max-w-[180px]"
              style={{ color: 'rgba(80,40,60,0.55)' }}>
              {citation.source || citation.id || `ref-${index + 1}`}
            </span>
          </div>
          <motion.span
            animate={{ rotate: open ? 180 : 0 }}
            style={{ color: 'rgba(80,40,60,0.3)', fontSize: 12 }}
          >▾</motion.span>
        </div>

        <AnimatePresence>
          {open && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ type: 'spring', stiffness: 300, damping: 28 }}
              className="overflow-hidden"
            >
              <div className="mt-2 pt-2 text-[11px] leading-relaxed"
                style={{ borderTop: `1px solid rgba(80,40,60,0.1)`, color: 'rgba(80,40,60,0.6)' }}>
                {citation.snippet || citation.content || citation.text || 'No preview available.'}
              </div>
              {citation.score != null && (
                <div className="mt-1.5 text-[10px] font-mono"
                  style={{ color: 'rgba(80,40,60,0.35)' }}>
                  score · {citation.score?.toFixed(3)}
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  )
}
