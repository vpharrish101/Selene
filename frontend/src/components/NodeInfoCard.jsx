import { motion } from 'framer-motion'

const SPRING = { type: 'spring', stiffness: 200, damping: 22 }

export default function NodeInfoCard({ node, onClose }) {
  if (!node) return null

  const props = node.properties || {}
  const sourceChunks = node.source_chunk_ids || []
  const sourceDocs = node.source_doc_ids || []

  return (
    <motion.div
      key={node.id}
      initial={{ opacity: 0, x: 20, scale: 0.95 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: 20, scale: 0.95 }}
      transition={SPRING}
      className="absolute z-50 w-72 rounded-2xl p-5 shadow-2xl overflow-hidden"
      style={{
        background: 'linear-gradient(145deg, rgba(20,5,15,0.92) 0%, rgba(10,0,5,0.96) 100%)',
        border: '1px solid rgba(224,88,32,0.25)',
        top: 24, right: 24,
        backdropFilter: 'blur(16px)',
        boxShadow: '0 20px 40px rgba(0,0,0,0.6), inset 0 0 20px rgba(224,88,32,0.05)',
      }}
    >
      {/* Decorative accent */}
      <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-[#e05820]/40 to-transparent" />

      <div className="flex items-start justify-between mb-4">
        <div className="flex-1 min-w-0">
          <div className="text-[9px] font-mono text-[#e05820]/70 uppercase tracking-[0.2em] mb-1 font-bold">
            {node.type || 'ENTITY'}
          </div>
          <div className="text-base font-bold text-white leading-tight truncate tracking-tight">
            {node.name}
          </div>
        </div>
        <button
          onClick={onClose}
          className="text-white/20 hover:text-white/60 transition-colors p-1 -mt-1 -mr-1"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>

      <div className="space-y-4">
        {/* Properties Section */}
        {Object.entries(props).length > 0 && (
          <div>
            <div className="text-[10px] font-mono text-white/30 uppercase tracking-widest mb-2 border-b border-white/5 pb-1">
              Attributes
            </div>
            <div className="grid grid-cols-1 gap-2">
              {Object.entries(props).map(([k, v]) => (
                <div key={k} className="flex flex-col">
                  <span className="text-[9px] font-mono text-white/20 uppercase">{k}</span>
                  <span className="text-[11px] text-white/80 font-medium break-words leading-relaxed">{String(v)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Sources Section */}
        {(sourceDocs.length > 0 || sourceChunks.length > 0) && (
          <div>
            <div className="text-[10px] font-mono text-white/30 uppercase tracking-widest mb-2 border-b border-white/5 pb-1">
              Knowledge Context
            </div>
            <div className="flex flex-wrap gap-1.5">
              {sourceDocs.map((id, i) => (
                <div key={`doc-${i}`} className="px-2 py-0.5 rounded bg-[#e05820]/10 border border-[#e05820]/20 text-[9px] text-[#ff9e7d] font-mono">
                  DOC:{String(id).slice(-6)}
                </div>
              ))}
              {sourceChunks.map((id, i) => (
                <div key={`chunk-${i}`} className="px-2 py-0.5 rounded bg-white/5 border border-white/10 text-[9px] text-white/40 font-mono">
                  CHUNK:{String(id).slice(-4)}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Footer Info */}
      <div className="mt-6 pt-3 border-t border-white/5 flex items-center justify-between">
         <div className="flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-[#e05820]/60 blur-[1px]" />
            <span className="text-[9px] font-mono text-white/20 uppercase tracking-tighter">
              Centrality: {node.importance?.toFixed(3) ?? '0.000'}
            </span>
         </div>
         <span className="text-[8px] font-mono text-white/10 italic">
            ID: {node.id?.slice(0, 8)}
         </span>
      </div>
    </motion.div>
  )
}

