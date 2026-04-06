import { useEffect, useRef, useState, useCallback, useMemo, memo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import NodeInfoCard from '../components/NodeInfoCard'
import { useGraphData } from '../hooks/useSelene'

const NODE_COLORS = {
  person:   '#ec4899', // soft pink
  project:  '#8b5cf6', // violet
  task:     '#22c55e', // green
  document: '#94a3b8', // slate
  event:    '#f59e0b', // amber
  unknown:  '#64748b', // default slate
}

// Seeded pseudorandom for stable star positions
function seededRand(seed) {
  let s = seed
  return () => {
    s = (s * 1664525 + 1013904223) & 0xffffffff
    return (s >>> 0) / 0xffffffff
  }
}

function Starfield() {
  const stars = useMemo(() => {
    const rand = seededRand(42)
    const out = []

    // Small sparkle stars
    for (let i = 0; i < 80; i++) {
      const x = rand() * 100
      const y = rand() * 100
      const r = 0.5 + rand() * 1.2
      const dur = 2 + rand() * 4
      const delay = -rand() * 6
      const alpha = 0.25 + rand() * 0.55
      out.push({
        key: `s${i}`, type: 'star',
        style: {
          left: `${x}%`, top: `${y}%`,
          width: r * 2, height: r * 2,
          opacity: alpha,
          '--tw-dur': `${dur}s`,
          '--tw-delay': `${delay}s`,
        },
      })
    }

    // Medium bokeh circles — soft red/pink
    for (let i = 0; i < 22; i++) {
      const x = rand() * 100
      const y = rand() * 100
      const r = 4 + rand() * 14
      const dur = 5 + rand() * 8
      const delay = -rand() * 10
      const colors = ['rgba(224,88,32,', 'rgba(194,24,91,', 'rgba(255,96,64,', 'rgba(180,10,60,']
      const col = colors[Math.floor(rand() * colors.length)]
      const alpha = 0.06 + rand() * 0.1
      out.push({
        key: `b${i}`, type: 'bokeh',
        style: {
          left: `${x}%`, top: `${y}%`,
          width: r * 2, height: r * 2,
          background: `${col}${alpha})`,
          '--bk-dur': `${dur}s`,
          '--bk-delay': `${delay}s`,
          '--bk-blur': `${3 + rand() * 8}px`,
        },
      })
    }

    return out
  }, [])

  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden z-0">
      {stars.map(s => (
        <div key={s.key} className={s.type} style={s.style} />
      ))}
    </div>
  )
}

function useForceGraph(containerRef, data, onNodeClick, highlightNodes, searchTerm) {
  const graphRef = useRef(null)

  useEffect(() => {
    const el = containerRef.current
    if (!el) return

    let fg
    const load = async () => {
      const { default: ForceGraph } = await import('force-graph')
      if (!containerRef.current) return

      fg = ForceGraph()(el)
        .width(el.clientWidth)
        .height(el.clientHeight)
        .backgroundColor('transparent')
        .graphData(data)
        .nodeRelSize(5)
        .nodeVal(n => {
           // Importance-based sizing: log degree or importance value
           const degree = data.links.filter(l => l.source.id === n.id || l.target.id === n.id).length
           const baseSize = 4 + (n.importance || 0) * 8 + Math.log(degree + 1) * 2
           
           if (searchTerm && n.name.toLowerCase().includes(searchTerm.toLowerCase())) return baseSize * 1.5
           return baseSize
        })
        .nodeLabel(() => '')
        .linkColor(l => {
          if (highlightNodes.size > 0) {
            const isRelated = highlightNodes.has(l.source.id) && highlightNodes.has(l.target.id)
            return isRelated ? 'rgba(255,255,255,0.4)' : 'rgba(255,255,255,0.03)'
          }
          return 'rgba(255,255,255,0.1)'
        })
        .linkWidth(l => (highlightNodes.size > 0 && highlightNodes.has(l.source.id) && highlightNodes.has(l.target.id)) ? 1.5 : 0.8)
        .linkDirectionalParticles(l => (highlightNodes.size > 0 && highlightNodes.has(l.source.id) && highlightNodes.has(l.target.id)) ? 2 : 0)
        .linkDirectionalParticleWidth(1.5)
        .linkDirectionalParticleSpeed(0.005)
        .nodeCanvasObject((node, ctx, globalScale) => {
          if (!isFinite(node.x) || !isFinite(node.y)) return
          
          const isSelected = highlightNodes.has(node.id)
          const hasSelection = highlightNodes.size > 0
          const isSearchMatch = searchTerm && node.name.toLowerCase().includes(searchTerm.toLowerCase())
          
          const color = NODE_COLORS[node.type?.toLowerCase()] || NODE_COLORS.unknown
          const r = Math.max(3, Math.sqrt(node.val || 4) * 2.5)
          
          // Focus + Fade opacity logic
          let opacity = 1
          if (hasSelection) {
            opacity = isSelected ? 1 : 0.15
          } else if (searchTerm) {
            opacity = isSearchMatch ? 1 : 0.2
          }

          ctx.globalAlpha = opacity

          // Node Glow
          const glow = ctx.createRadialGradient(node.x, node.y, 0, node.x, node.y, r * 2.5)
          glow.addColorStop(0, color + '60')
          glow.addColorStop(1, 'transparent')
          ctx.fillStyle = glow
          ctx.beginPath()
          ctx.arc(node.x, node.y, r * 2.5, 0, 2 * Math.PI)
          ctx.fill()

          // Node Body
          ctx.fillStyle = color
          ctx.beginPath()
          ctx.arc(node.x, node.y, r, 0, 2 * Math.PI)
          ctx.fill()
          
          // White ring for search matches or selection
          if (isSelected || isSearchMatch) {
            ctx.strokeStyle = '#ffffff'
            ctx.lineWidth = 1 / globalScale
            ctx.beginPath()
            ctx.arc(node.x, node.y, r + 1, 0, 2 * Math.PI)
            ctx.stroke()
          }

          // Label
          if (globalScale > 0.6 || isSelected || isSearchMatch) {
            const fs = (isSelected || isSearchMatch ? 12 : 9) / globalScale
            ctx.font = `${isSelected || isSearchMatch ? 'bold' : 'normal'} ${fs}px 'JetBrains Mono', monospace`
            ctx.fillStyle = isSelected || isSearchMatch ? '#ffffff' : 'rgba(255,255,255,0.7)'
            ctx.textAlign = 'center'
            ctx.textBaseline = 'top'
            ctx.fillText(node.name, node.x, node.y + r + 3)
          }

          ctx.globalAlpha = 1
        })
        .onNodeClick(node => onNodeClick(node))
        .cooldownTicks(100)
        .d3AlphaDecay(0.01)
        .d3VelocityDecay(0.3)
        .onNodeDragEnd(node => {
          node.fx = node.x;
          node.fy = node.y;
        })

      // Tuning forces
      fg.d3Force('charge').strength(-200)
      fg.d3Force('link').distance(70)

      graphRef.current = fg

      const ro = new ResizeObserver(() => {
        if (el && fg) fg.width(el.clientWidth).height(el.clientHeight)
      })
      ro.observe(el)
      graphRef._ro = ro
    }

    load()

    return () => {
      graphRef._ro?.disconnect()
      if (fg) { try { fg._destructor?.() } catch {} }
      if (el) el.innerHTML = ''
    }
  }, [data]) 

  useEffect(() => {
     if (graphRef.current) {
        graphRef.current.graphData(data)
     }
  }, [data])

  return graphRef;
}

export default function GraphPanel({ active, graphData: externalData }) {

  const { data: fullData, fetch: fetchAll } = useGraphData()
  const [searchTerm, setSearchTerm] = useState('')
  const [highlightNodes, setHighlightNodes] = useState(new Set())
  const [selectedNode, setSelectedNode] = useState(null)
  const containerRef = useRef(null)

  // Use external data (subgraph from query) if provided, otherwise use full data
  const data = useMemo(() => {
    if (externalData && externalData.nodes?.length > 0) return externalData
    return fullData || { nodes: [], links: [] }
  }, [externalData, fullData])

  useEffect(() => {
    fetchAll()
  }, [fetchAll])

  const handleNodeClick = useCallback(node => {
    setSelectedNode(prev => prev?.id === node.id ? null : node)
    
    // Highlight neighbors
    if (node) {
      const neighbors = new Set([node.id])
      data.links.forEach(l => {
        if (l.source.id === node.id) neighbors.add(l.target.id)
        if (l.target.id === node.id) neighbors.add(l.source.id)
      })
      setHighlightNodes(neighbors)
    } else {
      setHighlightNodes(new Set())
    }
  }, [data])

  const graphRef = useForceGraph(containerRef, data, handleNodeClick, highlightNodes, searchTerm)

  const handleZoom = (type) => {
    if (!graphRef.current) return
    const current = graphRef.current.zoom()
    if (type === 'in') graphRef.current.zoom(current * 1.5, 400)
    if (type === 'out') graphRef.current.zoom(current * 0.7, 400)
    if (type === 'fit') graphRef.current.zoomToFit(600)
  }

  return (
    <div className="relative w-full h-full overflow-hidden"
      style={{ background: 'radial-gradient(ellipse at 40% 30%, #2a0810 0%, #180308 60%, #0f0205 100%)' }}>

      {/* Starfield */}
      <Starfield />

      {/* Background Blobs */}
      <div className="blob z-1" style={{
        width: 280, height: 280, top: '10%', left: '15%',
        background: 'radial-gradient(circle, rgba(220,70,30,0.2) 0%, transparent 65%)',
        animationDuration: '9s',
      }} />
      <div className="blob blob-2 z-1" style={{
        width: 200, height: 200, top: '60%', right: '8%',
        background: 'radial-gradient(circle, rgba(180,20,70,0.15) 0%, transparent 65%)',
      }} />

      {/* Overlay Header */}
      <div className="absolute top-0 left-0 right-0 z-20 flex flex-col p-4 pointer-events-none">
        <div className="flex items-center justify-between w-full">
           <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full"
              style={{ background: '#e05820', boxShadow: '0 0 5px #e05820' }} />
            <span className="text-[10px] font-mono uppercase tracking-widest"
              style={{ color: 'rgba(224,88,32,0.7)' }}>
              Knowledge Graph
            </span>
          </div>
          <div className="flex items-center gap-3 pointer-events-auto">
             <div className="relative group">
                <input 
                  type="text"
                  placeholder="SEARCH ENTITY..."
                  value={searchTerm}
                  onChange={e => setSearchTerm(e.target.value)}
                  className="bg-black/40 border border-white/10 px-3 py-1 text-[9px] font-mono tracking-tighter focus:outline-none focus:border-[#e05820]/40 w-32 transition-all focus:w-48"
                  style={{ color: '#ffb39b' }}
                />
                {searchTerm && (
                   <button onClick={() => setSearchTerm('')} className="absolute right-2 top-1.5 text-[8px] text-white/30 hover:text-white/60">✕</button>
                )}
             </div>
             <span className="text-[9px] font-mono" style={{ color: 'rgba(224,88,32,0.4)' }}>
                {data.nodes?.length}n · {data.links?.length}e
              </span>
          </div>
        </div>
      </div>

      {/* Zoom Controls */}
      <div className="absolute bottom-6 right-6 z-20 flex flex-col gap-2">
         {[
           { id: 'in',  label: '+', onClick: () => handleZoom('in') },
           { id: 'out', label: '−', onClick: () => handleZoom('out') },
           { id: 'fit', label: '▣', onClick: () => handleZoom('fit') },
         ].map(btn => (
           <button
             key={btn.id}
             onClick={btn.onClick}
             className="w-7 h-7 bg-black/50 border border-white/10 flex items-center justify-center text-xs text-white/40 hover:text-[#e05820] hover:border-[#e05820]/30 transition-colors"
           >
             {btn.label}
           </button>
         ))}
      </div>

      {/* Force graph */}
      <div ref={containerRef} className="absolute inset-0 z-5" />

      {/* Node info card */}
      <AnimatePresence>
        {selectedNode && (
          <NodeInfoCard 
            node={selectedNode} 
            onClose={() => {
              setSelectedNode(null)
              setHighlightNodes(new Set())
            }} 
          />
        )}
      </AnimatePresence>

      {/* Empty State / Loading */}
      {!data.nodes?.length && (
         <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-10">
            <span className="text-[10px] font-mono tracking-widest text-white/20 animate-pulse">
               INITIALIZING NEURAL FABRIC...
            </span>
         </div>
      )}

      {/* Bottom fade */}
      <div className="absolute bottom-0 left-0 right-0 h-16 pointer-events-none z-10"
        style={{ background: 'linear-gradient(to top, rgba(15,2,5,0.8) 0%, transparent 100%)' }} />
    </div>
  )
}

