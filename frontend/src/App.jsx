import { useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import GraphPanel from './panels/GraphPanel'
import QueryPanel from './panels/QueryPanel'
import SystemPanel from './panels/SystemPanel'

const SPRING = { type: 'spring', stiffness: 120, damping: 20 }

const PANEL_CFG = {
  graph:  {
    label: 'GRAPH',
    color: '#e05820',
    collapsed: 'linear-gradient(180deg, rgba(42,0,15,0.95) 0%, rgba(74,0,32,0.9) 100%)',
    border: 'rgba(194,24,91,0.2)',
  },
  query:  {
    label: 'QUERY',
    color: '#00bcd4',
    collapsed: 'linear-gradient(180deg, rgba(0,0,58,0.95) 0%, rgba(0,0,90,0.9) 100%)',
    border: 'rgba(0,188,212,0.15)',
  },
  system: {
    label: 'SYSTEM',
    color: '#80cbc4',
    collapsed: 'linear-gradient(180deg, rgba(232,207,192,0.96) 0%, rgba(240,217,200,0.92) 100%)',
    border: 'none',
  },
}

function CollapsedOverlay({ cfg }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="absolute inset-0 z-20 flex items-center justify-center"
      style={{ background: cfg.collapsed, backdropFilter: 'blur(2px)' }}
    >
      {/* Ambient glow dot */}
      <div className="absolute top-1/3"
        style={{
          width: 40, height: 40,
          borderRadius: '50%',
          background: `radial-gradient(circle, ${cfg.color}60 0%, transparent 70%)`,
          filter: 'blur(8px)',
        }}
      />
      <span
        className="panel-label"
        style={{ color: cfg.color, opacity: 0.7 }}
      >
        {cfg.label}
      </span>
    </motion.div>
  )
}

function PanelShell({ id, active, onClick, children }) {
  const cfg = PANEL_CFG[id]
  const flexVal = active ? 18 : 1

  return (
    <motion.div
      layout
      animate={{ flex: flexVal }}
      transition={SPRING}
      onClick={!active ? onClick : undefined}
      className="relative h-full overflow-hidden flex-shrink-0"
      style={{
        flex: flexVal,
        cursor: active ? 'default' : 'pointer',
        borderRight: id !== 'system' ? `1px solid ${cfg.border}` : 'none',
        minWidth: 0,
      }}
    >
      {/* Panel content — fades when inactive */}
      <motion.div
        className="absolute inset-0"
        animate={{ opacity: active ? 1 : 0.15 }}
        transition={{ duration: 0.3 }}
      >
        {children}
      </motion.div>

      {/* Collapsed overlay */}
      {!active && <CollapsedOverlay cfg={cfg} />}
    </motion.div>
  )
}

export default function App() {
  const [active, setActive] = useState('query')
  const [graphData, setGraphData] = useState(null)
  const [queryHistory, setQueryHistory] = useState([])

  const handleQueryResult = useCallback((result) => {
    if (result?.subgraph) setGraphData(result.subgraph)
  }, [])

  return (
    <div className="w-screen h-screen flex overflow-hidden" style={{ background: '#050010' }}>

      {/* Selene wordmark — centered, always visible */}
      <div className="absolute top-0 left-0 right-0 flex items-center justify-center pt-2.5 z-50 pointer-events-none">
        <div className="flex items-center gap-2">
          <div className="w-px h-3 opacity-20" style={{ background: PANEL_CFG[active].color }} />
          <span className="text-[10px] font-mono tracking-[0.4em] uppercase"
            style={{ color: `${PANEL_CFG[active].color}80` }}>
            selene
          </span>
          <div className="w-px h-3 opacity-20" style={{ background: PANEL_CFG[active].color }} />
        </div>
      </div>

      {/* LEFT — Knowledge Graph (Warm palette) */}
      <PanelShell id="graph" active={active === 'graph'} onClick={() => setActive('graph')}>
        <GraphPanel active={active === 'graph'} graphData={graphData} />
      </PanelShell>

      {/* CENTER — Query + Reasoning (Cold palette) */}
      <PanelShell id="query" active={active === 'query'} onClick={() => setActive('query')}>
        <QueryPanel
          onQueryResult={handleQueryResult}
          queryHistory={queryHistory}
          setQueryHistory={setQueryHistory}
        />
      </PanelShell>

      {/* RIGHT — Service Layer (Pastel palette) */}
      <PanelShell id="system" active={active === 'system'} onClick={() => setActive('system')}>
        <SystemPanel />
      </PanelShell>
    </div>
  )
}
