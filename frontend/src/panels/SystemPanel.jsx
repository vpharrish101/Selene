import { useState, useCallback, memo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { callApi, useStats } from '../hooks/useSelene'

const SPRING = { type: 'spring', stiffness: 140, damping: 22 }

const ENDPOINTS = [
  {
    id: 'ingest', method: 'POST', path: '/ingest', label: 'Ingest Document',
    fields: [
      { key: 'text', label: 'Document text', type: 'textarea', placeholder: 'Paste document content…' },
      { key: 'source', label: 'Source name', type: 'text', placeholder: 'document.pdf' },
    ],
    wide: true,
  },
  {
    id: 'query', method: 'POST', path: '/query', label: 'Query',
    fields: [
      { key: 'query', label: 'Query', type: 'text', placeholder: 'Your question…' },
      { key: 'top_k', label: 'Top K', type: 'number', placeholder: '5' },
    ],
  },
  {
    id: 'search', method: 'GET', path: '/search', label: 'Search',
    fields: [{ key: 'q', label: 'Query', type: 'text', placeholder: 'Search term…' }],
  },
  {
    id: 'entity', method: 'GET', path: '/graph/entity/{name}', label: 'Get Entity',
    fields: [{ key: 'name', label: 'Entity name', type: 'text', placeholder: 'Tesla' }],
    pathParam: 'name',
  },
  {
    id: 'path', method: 'GET', path: '/graph/path', label: 'Graph Path',
    fields: [
      { key: 'source', label: 'Source', type: 'text', placeholder: 'NodeA' },
      { key: 'target', label: 'Target', type: 'text', placeholder: 'NodeB' },
    ],
  },
  {
    id: 'debug', method: 'GET', path: '/debug/retrieval', label: 'Debug Retrieval',
    fields: [{ key: 'q', label: 'Debug query', type: 'text', placeholder: 'query…' }],
  },
  {
    id: 'stats', method: 'GET', path: '/stats', label: 'System Stats',
    fields: [],
    noInput: true,
  },
]

const METHOD_STYLE = {
  GET:  { bg: 'rgba(128,203,196,0.15)', border: 'rgba(128,203,196,0.4)', text: '#80cbc4' },
  POST: { bg: 'rgba(244,143,177,0.12)', border: 'rgba(244,143,177,0.35)', text: '#f48fb1' },
}

function ApiCard({ ep, index }) {
  const [vals, setVals] = useState({})
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [open, setOpen] = useState(false)

  const ms = METHOD_STYLE[ep.method] || METHOD_STYLE.GET

  const run = useCallback(async () => {
    setLoading(true)
    try {
      let path = ep.path
      const params = {}
      const body = {}

      ep.fields?.forEach(f => {
        const v = vals[f.key] || ''
        if (ep.pathParam === f.key) {
          path = path.replace(`{${f.key}}`, encodeURIComponent(v))
        } else if (ep.method === 'GET') {
          if (v) params[f.key] = v
        } else {
          if (v) body[f.key] = f.type === 'number' ? Number(v) : v
        }
      })

      const data = await callApi(path, ep.method, Object.keys(body).length ? body : null, params)
      setResult(data)
      setOpen(true)
    } catch (e) {
      setResult({ error: e.message })
      setOpen(true)
    }
    setLoading(false)
  }, [ep, vals])

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ ...SPRING, delay: index * 0.04 }}
      className="rounded-xl mb-3"
      style={{
        background: 'rgba(245,235,224,0.6)',
        border: '1px solid rgba(128,203,196,0.2)',
        backdropFilter: 'blur(8px)',
      }}
    >
      <div className="p-3">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded"
              style={{ background: ms.bg, border: `1px solid ${ms.border}`, color: ms.text }}>
              {ep.method}
            </span>
            <span className="text-xs font-semibold" style={{ color: '#2d1a10' }}>{ep.label}</span>
          </div>
          <span className="text-[9px] font-mono" style={{ color: '#80cbc4' }}>
            {ep.path.length > 20 ? '…' + ep.path.slice(-16) : ep.path}
          </span>
        </div>

        {ep.fields?.map(f => (
          <div key={f.key} className="mb-2">
            <div className="text-[9px] font-mono uppercase tracking-wider mb-1" style={{ color: '#80a0a0' }}>
              {f.label}
            </div>
            {f.type === 'textarea' ? (
              <textarea rows={3} placeholder={f.placeholder}
                value={vals[f.key] || ''} onChange={e => setVals(v => ({ ...v, [f.key]: e.target.value }))}
                className="w-full rounded-lg px-3 py-2 text-xs font-mono resize-none"
                style={{ background: 'rgba(255,255,255,0.6)', border: '1px solid rgba(128,203,196,0.3)',
                  color: '#2d1a10', outline: 'none' }} />
            ) : (
              <input type={f.type || 'text'} placeholder={f.placeholder}
                value={vals[f.key] || ''} onChange={e => setVals(v => ({ ...v, [f.key]: e.target.value }))}
                className="w-full rounded-lg px-3 py-2 text-xs font-mono"
                style={{ background: 'rgba(255,255,255,0.6)', border: '1px solid rgba(128,203,196,0.3)',
                  color: '#2d1a10', outline: 'none' }} />
            )}
          </div>
        ))}

        <button onClick={run} disabled={loading}
          className="w-full rounded-lg py-1.5 text-xs font-mono font-semibold transition-all disabled:opacity-50"
          style={{ background: 'rgba(77,182,172,0.2)', border: '1px solid rgba(77,182,172,0.4)', color: '#4db6ac' }}>
          {loading ? '···' : '▶ Execute'}
        </button>
      </div>

      <AnimatePresence>
        {open && result && (
          <motion.div initial={{ height: 0 }} animate={{ height: 'auto' }} exit={{ height: 0 }}
            transition={SPRING} className="overflow-hidden">
            <div className="border-t px-3 pb-3" style={{ borderColor: 'rgba(128,203,196,0.15)' }}>
              <div className="flex items-center justify-between pt-2 mb-1">
                <span className="text-[9px] font-mono uppercase tracking-wider" style={{ color: '#80a0a0' }}>
                  response
                </span>
                <button onClick={() => setOpen(false)}
                  className="text-[10px]" style={{ color: '#b0c0c0' }}>✕</button>
              </div>
              <pre className="json-view rounded-lg p-2 max-h-40 overflow-y-auto text-[10px]"
                style={{ background: 'rgba(255,255,255,0.5)', color: '#2d3020' }}>
                {JSON.stringify(result, null, 2)}
              </pre>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

function StatBox({ label, value, color }) {
  return (
    <div className="rounded-xl p-3 flex-1" style={{
      background: 'rgba(245,235,224,0.5)',
      border: `1px solid ${color}30`,
    }}>
      <div className="text-[9px] font-mono uppercase tracking-widest mb-1" style={{ color: '#80a0a0' }}>
        {label}
      </div>
      <div className="text-xl font-light font-mono" style={{ color }}>
        {value ?? '—'}
      </div>
    </div>
  )
}

function SystemPanel() {
  const { data: statsData, fetch: fetchStats, loading: statsLoading } = useStats()

  return (
    <div className="relative w-full h-full overflow-hidden" style={{ background: '#f5ebe0' }}>
      {/* Pastel fluid blobs */}
      <div className="blob" style={{
        width: 250, height: 250, top: '5%', right: '10%',
        background: 'radial-gradient(circle, rgba(244,143,177,0.25) 0%, transparent 70%)',
        animationDuration: '12s',
      }} />
      <div className="blob blob-2" style={{
        width: 180, height: 180, bottom: '20%', left: '5%',
        background: 'radial-gradient(circle, rgba(128,203,196,0.3) 0%, transparent 70%)',
      }} />
      <div className="blob blob-3" style={{
        width: 130, height: 130, top: '50%', right: '20%',
        background: 'radial-gradient(circle, rgba(77,182,172,0.2) 0%, transparent 70%)',
      }} />

      <div className="relative z-10 h-full flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-5 pt-4 pb-3 flex-shrink-0">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full glow-pulse" style={{ background: '#80cbc4' }} />
            <span className="text-[10px] font-mono uppercase tracking-widest" style={{ color: '#80a0a0' }}>
              Service Layer
            </span>
          </div>
        </div>

        {/* Stats */}
        <div className="px-4 pb-3 flex-shrink-0">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[9px] font-mono uppercase tracking-widest" style={{ color: '#a0b0b0' }}>
              system state
            </span>
            <button onClick={fetchStats} disabled={statsLoading}
              className="text-[9px] font-mono px-2 py-1 rounded transition-all"
              style={{ background: 'rgba(128,203,196,0.15)', border: '1px solid rgba(128,203,196,0.3)',
                color: '#4db6ac' }}>
              {statsLoading ? '···' : '↻ refresh'}
            </button>
          </div>
          <div className="flex gap-2">
            <StatBox label="nodes" value={statsData?.total_nodes} color="#80cbc4" />
            <StatBox label="edges" value={statsData?.total_edges} color="#f48fb1" />
            <StatBox label="docs" value={statsData?.total_documents} color="#4db6ac" />
          </div>
        </div>

        <div className="mx-4 mb-3 h-px" style={{ background: 'rgba(128,203,196,0.2)' }} />

        {/* API Cards */}
        <div className="flex-1 overflow-y-auto px-4 pb-4">
          <div className="text-[9px] font-mono uppercase tracking-widest mb-3" style={{ color: '#a0b0b0' }}>
            endpoints
          </div>
          {ENDPOINTS.map((ep, i) => (
            <ApiCard key={ep.id} ep={ep} index={i} />
          ))}
        </div>
      </div>
    </div>
  )
}

export default memo(SystemPanel)
