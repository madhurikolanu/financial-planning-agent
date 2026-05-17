import { useState, useEffect } from 'react'
import { api } from './api'
import Dashboard from './pages/Dashboard'
import ControlPanel from './pages/ControlPanel'
import Profiles from './pages/Profiles'
import RunHistory from './pages/RunHistory'
import AgentLogs from './pages/AgentLogs'

const NAV = [
  { id: 'dashboard',  label: 'Dashboard',     icon: 'ti-chart-bar' },
  { id: 'control',    label: 'Control panel',  icon: 'ti-settings' },
  { id: 'profiles',   label: 'Profiles',       icon: 'ti-user' },
  { id: 'history',    label: 'Run history',    icon: 'ti-clock' },
  { id: 'logs',       label: 'Agent logs',     icon: 'ti-file' },
]

export default function App() {
  const [page,   setPage]   = useState('dashboard')
  const [status, setStatus] = useState(null)
  const [online, setOnline] = useState(false)

  useEffect(() => {
    checkStatus()
    const interval = setInterval(checkStatus, 10000) // refresh every 10s
    return () => clearInterval(interval)
  }, [])

  async function checkStatus() {
    try {
      const s = await api.getStatus()
      setStatus(s)
      setOnline(true)
    } catch {
      setStatus(null)
      setOnline(false)
    }
  }

  const pages = {
    dashboard: <Dashboard />,
    control:   <ControlPanel />,
    profiles:  <Profiles />,
    history:   <RunHistory />,
    logs:      <AgentLogs />,
  }

  const a1 = status?.agents?.agent1?.state ?? 'OFFLINE'
  const a2 = status?.agents?.agent2?.state ?? 'OFFLINE'
  const a3 = status?.agents?.agent3?.state ?? 'OFFLINE'

  return (
    <div style={{ display: 'flex', height: '100vh', fontFamily: 'Inter, sans-serif' }}>

      {/* Sidebar */}
      <div style={{
        width: 220, background: '#fff', borderRight: '1px solid #eee',
        display: 'flex', flexDirection: 'column', flexShrink: 0
      }}>
        <div style={{ padding: '18px 16px', borderBottom: '1px solid #eee' }}>
          <div style={{ fontWeight: 600, fontSize: 14, color: '#111' }}>Financial Agent</div>
          <div style={{ fontSize: 11, marginTop: 3, display: 'flex', alignItems: 'center', gap: 5 }}>
            <div style={{
              width: 6, height: 6, borderRadius: '50%',
              background: online ? '#1D9E75' : '#E24B4A'
            }} />
            <span style={{ color: online ? '#1D9E75' : '#A32D2D' }}>
              {online ? 'backend online' : 'backend offline'}
            </span>
          </div>
        </div>

        <nav style={{ padding: 8, flex: 1 }}>
          {NAV.map(n => (
            <div
              key={n.id}
              onClick={() => setPage(n.id)}
              style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '8px 10px', borderRadius: 8, cursor: 'pointer',
                fontSize: 13, marginBottom: 2,
                background: page === n.id ? '#f5f5f5' : 'transparent',
                fontWeight: page === n.id ? 500 : 400,
                color: page === n.id ? '#111' : '#555',
              }}
            >
              <i className={`ti ${n.icon}`} style={{ fontSize: 16 }} />
              {n.label}
            </div>
          ))}
        </nav>

        <div style={{ padding: 12, borderTop: '1px solid #eee' }}>
          <AgentDot label="Agent 1 — planner"   state={a1} />
          <AgentDot label="Agent 2 — executor"  state={a2} />
          <AgentDot label="Agent 3 — scheduler" state={a3} />
        </div>
      </div>

      {/* Main */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', background: '#fafafa', overflow: 'hidden' }}>
        <div style={{
          padding: '14px 20px', borderBottom: '1px solid #eee',
          background: '#fff', display: 'flex', justifyContent: 'space-between', alignItems: 'center'
        }}>
          <span style={{ fontWeight: 500, fontSize: 15, color: '#111' }}>
            {NAV.find(n => n.id === page)?.label}
          </span>
          {status?.next_scheduled_run && (
            <span style={{ fontSize: 12, color: '#888' }}>
              next run: {status.next_scheduled_run.slice(0, 16).replace('T', ' ')}
            </span>
          )}
        </div>
        <div style={{ flex: 1, overflow: 'auto' }}>
          {pages[page]}
        </div>
      </div>
    </div>
  )
}

function AgentDot({ label, state }) {
  const color = state === 'IDLE'    ? '#1D9E75'
              : state === 'OFFLINE' ? '#E24B4A'
              : '#BA7517'           // any active state

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: '#666', marginBottom: 5 }}>
      <div style={{ width: 6, height: 6, borderRadius: '50%', background: color, flexShrink: 0 }} />
      <span>{label}</span>
      <span style={{ marginLeft: 'auto', fontSize: 10, color }}>{state}</span>
    </div>
 
 )
}