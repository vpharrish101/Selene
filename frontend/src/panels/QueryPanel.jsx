import { useState, useRef, useCallback, useEffect, memo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useQuery } from '../hooks/useSelene'
import Citation from '../components/Citation'

const SPRING = { type: 'spring', stiffness: 150, damping: 22 }

// Pastel color tokens
const P = {
  bg:       '#fdf0f6',
  surface:  'rgba(255,255,255,0.7)',
  accent:   '#00897b',       // deeper mint
  accent2:  '#d81b60',       // deeper pink
  muted:    '#4db6ac',       // mint
  border:   'rgba(0,137,123,0.28)',
  border2:  'rgba(216,27,96,0.25)',
  text:     '#1a0a14',
  textMid:  '#4a1e38',
  textFaint:'rgba(60,20,45,0.62)',
  input:    'rgba(255,255,255,0.8)',
}

function ConfidenceBar({ value }) {
  const pct = Math.round((value || 0) * 100)
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1 rounded-full" style={{ background: 'rgba(77,182,172,0.15)' }}>
        <motion.div
          className="h-full rounded-full"
          style={{ background: 'linear-gradient(90deg, #4db6ac, #ec407a)' }}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ ...SPRING, delay: 0.15 }}
        />
      </div>
      <span className="text-[10px] font-mono" style={{ color: P.accent }}>{pct}%</span>
    </div>
  )
}

function MiniGraphCanvas({ entities }) {
  const containerRef = useRef(null)
  const graphRef = useRef(null)

  useEffect(() => {
    const el = containerRef.current
    if (!el || !entities?.length) return

    const nodes = entities.slice(0, 14).map((e, i) => ({
      id: e, name: e,
      importance: i === 0 ? 1.0 : 0.35 + Math.random() * 0.45,
    }))
    const links = []
    nodes.slice(1).forEach(n => links.push({ source: nodes[0].id, target: n.id }))
    for (let i = 1; i < nodes.length - 1; i += 3) {
      if (nodes[i + 1]) links.push({ source: nodes[i].id, target: nodes[i + 1].id })
    }

    const load = async () => {
      const { default: ForceGraph } = await import('force-graph')
      if (!containerRef.current) return

      const fg = ForceGraph()(el)
        .width(el.clientWidth || 280)
        .height(el.clientHeight || 280)
        .backgroundColor('transparent')
        .graphData({ nodes, links })
        .nodeRelSize(4)
        .nodeLabel(() => '')
        .linkColor(() => 'rgba(77,182,172,0.25)')
        .linkWidth(1)
        .nodeCanvasObject((node, ctx, gs) => {
          if (!isFinite(node.x) || !isFinite(node.y)) return
          const r = Math.max(3, Math.sqrt(node.importance || 0.5) * 6)
          const col = node.importance > 0.8 ? '#ec407a' : '#4db6ac'
          const g = ctx.createRadialGradient(node.x, node.y, 0, node.x, node.y, r * 2.5)
          g.addColorStop(0, col + '55')
          g.addColorStop(1, 'transparent')
          ctx.fillStyle = g
          ctx.beginPath()
          ctx.arc(node.x, node.y, r * 2.5, 0, Math.PI * 2)
          ctx.fill()
          ctx.fillStyle = col
          ctx.beginPath()
          ctx.arc(node.x, node.y, r, 0, Math.PI * 2)
          ctx.fill()
          if (gs > 0.4) {
            const fs = Math.max(6, 8 / gs)
            ctx.font = `${fs}px 'JetBrains Mono', monospace`
            ctx.fillStyle = 'rgba(45,16,32,0.65)'
            ctx.textAlign = 'center'
            ctx.textBaseline = 'top'
            ctx.fillText(node.name, node.x, node.y + r + 2)
          }
        })
        .enableNodeDrag(false)
        .enableZoomInteraction(false)
        .cooldownTicks(60)
        .d3AlphaDecay(0.07)
        .d3VelocityDecay(0.4)

      graphRef.current = fg
    }

    load()

    return () => {
      if (graphRef.current) { try { graphRef.current._destructor?.() } catch {} }
      if (el) el.innerHTML = ''
      graphRef.current = null
    }
  }, [entities?.join(',')])

  return <div ref={containerRef} className="w-full h-full" />
}

function MiniGraph({ entities }) {
  if (!entities?.length) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3" style={{ opacity: 0.3 }}>
        <motion.div
          animate={{ scale: [1, 1.08, 1], opacity: [0.4, 0.7, 0.4] }}
          transition={{ repeat: Infinity, duration: 2.8 }}
          className="text-3xl font-mono" style={{ color: P.accent }}>◈</motion.div>
        <span className="text-[9px] font-mono uppercase tracking-widest" style={{ color: P.textMid }}>
          awaiting query
        </span>
      </div>
    )
  }
  return <MiniGraphCanvas entities={entities} />
}

const MiniGraphMemo = memo(MiniGraph, (prev, next) =>
  prev.entities?.join(',') === next.entities?.join(',')
)

function QueryPanel({ onQueryResult, queryHistory, setQueryHistory }) {
  const [input, setInput] = useState('')
  const { data, loading, error, run } = useQuery()

  const hasData = !!(data || error)

  const entities = data?.entities
    || data?.reasoning_trace?.entities
    || data?.subgraph?.nodes?.map(n => n.name || n.id)
    || []

  const handleSubmit = useCallback(async (q) => {
    const text = q !== undefined ? q : input.trim()
    if (!text) return
    const result = await run(text)
    if (result) {
      setQueryHistory(prev => [{ text, result, ts: Date.now() }, ...prev.slice(0, 19)])
      onQueryResult?.(result)
    }
  }, [input, run, onQueryResult, setQueryHistory])

  const handleKey = useCallback((e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit() }
  }, [handleSubmit])

  const citations = data?.citations || data?.sources || []
  const evidence  = data?.evidence || data?.reasoning_trace?.evidence || []

  return (
    <div className="pastel relative w-full h-full flex" style={{ background: P.bg }}>

      {/* Pastel fluid blobs — warm */}
      <div className="blob" style={{
        width: 300, height: 300, top: '10%', left: '20%',
        background: 'radial-gradient(circle, rgba(244,143,177,0.25) 0%, transparent 65%)',
        animationDuration: '10s',
      }} />
      <div className="blob blob-2" style={{
        width: 220, height: 220, bottom: '15%', left: '5%',
        background: 'radial-gradient(circle, rgba(128,203,196,0.28) 0%, transparent 65%)',
      }} />
      <div className="blob blob-3" style={{
        width: 160, height: 160, top: '55%', right: '22%',
        background: 'radial-gradient(circle, rgba(236,64,122,0.12) 0%, transparent 65%)',
      }} />

      {/* LEFT: Query + Answer */}
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden relative">

        {/* Animated top spacer — centers input when idle */}
        <motion.div
          animate={{ height: hasData ? 0 : '28%' }}
          transition={SPRING}
          style={{ flexShrink: 0, overflow: 'hidden' }}
        />

        {/* Header */}
        <div className="flex items-center gap-2 px-5 pb-2 flex-shrink-0">
          <span className="w-1.5 h-1.5 rounded-full"
            style={{ background: P.accent, boxShadow: `0 0 5px ${P.accent}` }} />
          <span className="text-[10px] font-mono uppercase tracking-widest"
            style={{ color: P.textMid }}>
            Query Interface
          </span>
        </div>

        {/* Input row */}
        <div className="px-5 pb-3 flex-shrink-0 flex gap-2">
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
            rows={2}
            placeholder="Ask anything about the knowledge graph…"
            className="pastel-input flex-1 resize-none rounded-xl px-4 py-3 text-sm font-mono transition-all"
            style={{
              background: P.input,
              border: `1px solid ${P.border}`,
              color: P.text,
              caretColor: P.accent,
              outline: 'none',
            }}
          />
          <button
            onClick={() => handleSubmit()}
            disabled={loading || !input.trim()}
            className="px-5 rounded-xl text-xs font-mono font-semibold transition-all disabled:opacity-35 flex-shrink-0 flex flex-col items-center justify-center gap-0.5"
            style={{
              background: 'rgba(77,182,172,0.15)',
              border: `1px solid ${P.border}`,
              color: P.accent,
              minWidth: 60,
            }}
          >
            {loading
              ? <motion.span animate={{ opacity: [0.4,1,0.4] }} transition={{ repeat: Infinity, duration: 1.2 }}>···</motion.span>
              : <>⏎<span className="text-[8px] opacity-50">run</span></>
            }
          </button>
        </div>

        {/* Divider */}
        <div className="mx-5 mb-3 h-px" style={{
          background: `linear-gradient(90deg, ${P.accent}44, transparent)`,
        }} />

        {/* Results area */}
        <div className="flex-1 overflow-y-auto px-5 pb-4 space-y-4 min-h-0">
          <AnimatePresence mode="wait">
            {error && (
              <motion.div key="err" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                className="rounded-xl p-3 text-xs font-mono"
                style={{ background: 'rgba(236,64,122,0.08)', border: `1px solid ${P.border2}`, color: P.accent2 }}>
                {error}
              </motion.div>
            )}

            {data && (
              <motion.div key="result" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                transition={SPRING} className="space-y-4">

                {/* Answer */}
                <div className="rounded-2xl p-4" style={{
                  background: P.surface,
                  border: `1px solid ${P.border}`,
                  backdropFilter: 'blur(8px)',
                }}>
                  <div className="text-[9px] font-mono uppercase tracking-widest mb-2"
                    style={{ color: P.textFaint }}>answer</div>
                  <p className="text-sm leading-relaxed" style={{ color: P.text }}>
                    {data.answer || data.response || 'No answer returned.'}
                  </p>
                  {data.confidence != null && (
                    <div className="mt-3">
                      <div className="text-[9px] font-mono uppercase tracking-widest mb-1"
                        style={{ color: P.textFaint }}>confidence</div>
                      <ConfidenceBar value={data.confidence} />
                    </div>
                  )}
                </div>

                {/* Evidence */}
                {evidence.length > 0 && (
                  <div>
                    <div className="text-[9px] font-mono uppercase tracking-widest mb-2"
                      style={{ color: P.textFaint }}>evidence</div>
                    {evidence.slice(0, 4).map((ev, i) => (
                      <div key={i} className="flex gap-2 mb-2.5">
                        <div className="w-4 h-4 rounded-full flex-shrink-0 flex items-center justify-center mt-0.5"
                          style={{ background: 'rgba(77,182,172,0.12)', border: `1px solid ${P.border}` }}>
                          <span className="text-[8px] font-mono" style={{ color: P.accent }}>{i + 1}</span>
                        </div>
                        <p className="text-xs leading-relaxed" style={{ color: P.textMid }}>{ev}</p>
                      </div>
                    ))}
                  </div>
                )}

                {/* Citations */}
                {citations.length > 0 && (
                  <div>
                    <div className="text-[9px] font-mono uppercase tracking-widest mb-2"
                      style={{ color: P.textFaint }}>citations</div>
                    {citations.map((c, i) => (
                      <Citation key={i} citation={typeof c === 'string' ? { source: c } : c} index={i} />
                    ))}
                  </div>
                )}
              </motion.div>
            )}

            {!data && !loading && !error && (
              <motion.div key="idle" initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                className="flex flex-col items-center justify-center gap-3 pt-6">
                <motion.div
                  animate={{ rotate: [0, 90, 180, 270, 360] }}
                  transition={{ repeat: Infinity, duration: 9, ease: 'linear' }}
                  className="text-4xl font-thin" style={{ color: P.accent }}>◈</motion.div>
                <p className="text-xs font-mono text-center leading-loose" style={{ color: P.textMid }}>
                  Selene awaits your query<br />
                  <span style={{ color: P.accent }}>graph + vector · hybrid reasoning</span>
                </p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Vertical divider */}
      <div className="w-px flex-shrink-0" style={{ background: P.border }} />

      {/* RIGHT: Mini graph + history */}
      <div className="w-72 flex-shrink-0 flex flex-col overflow-hidden">
        <div className="flex items-center gap-2 px-4 pt-4 pb-2 flex-shrink-0">
          <span className="w-1 h-1 rounded-full" style={{ background: P.muted }} />
          <span className="text-[10px] font-mono uppercase tracking-widest"
            style={{ color: P.textFaint }}>Reasoning Graph</span>
        </div>

        <div className="flex-1 relative min-h-0">
          <MiniGraphMemo entities={entities} />
        </div>

        {queryHistory.length > 0 && (
          <div className="flex-shrink-0 border-t px-4 py-3 max-h-44 overflow-y-auto"
            style={{ borderColor: P.border }}>
            <div className="text-[9px] font-mono uppercase tracking-widest mb-2"
              style={{ color: P.textFaint }}>history</div>
            {queryHistory.map((h) => (
              <button key={h.ts}
                onClick={() => { setInput(h.text); handleSubmit(h.text) }}
                className="w-full text-left mb-1 rounded-lg px-2 py-1.5 transition-all"
                style={{ background: 'rgba(77,182,172,0.06)' }}
                onMouseEnter={e => e.currentTarget.style.background = 'rgba(77,182,172,0.15)'}
                onMouseLeave={e => e.currentTarget.style.background = 'rgba(77,182,172,0.06)'}>
                <div className="text-[10px] font-mono truncate" style={{ color: P.textMid }}>
                  {h.text}
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default memo(QueryPanel)
