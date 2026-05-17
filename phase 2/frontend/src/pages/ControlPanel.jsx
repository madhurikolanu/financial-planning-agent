import { useEffect, useState } from 'react'
import { api } from '../api'

export default function ControlPanel() {
  const [status,   setStatus]   = useState(null)
  const [running,  setRunning]  = useState(false)
  const [result,   setResult]   = useState(null)
  const [error,    setError]    = useState(null)

  useEffect(() => { loadStatus() }, [])

  async function loadStatus() {
    try {
      const s = await api.getStatus()
      setStatus(s)
    } catch { setError('Cannot reach backend') }
  }

  async function runAll() {
    setRunning(true)
    setResult(null)
    setError(null)
    try {
      const r = await api.runScheduler()
      setResult(r)
      await loadStatus()
    } catch (e) {
      setError(e.response?.data?.detail || 'Run failed')
    } finally {
      setRunning(false)
    }
  }

  const sched = status?.agents?.agent3
  const a1    = status?.agents?.agent1
  const a2    = status?.agents?.agent2

  return (
    <div style={{ padding: 20 }}>

      {/* Agent status */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 16 }}>
        <AgentCard name="Agent 1" role="planner"    state={a1?.state} />
        <AgentCard name="Agent 2" role="executor"   state={a2?.state} />
        <AgentCard name="Agent 3" role="scheduler"  state={sched?.state} />
      </div>

      {/* Next scheduled run */}
      {status?.next_scheduled_run && (
        <div style={{
          background: '#EAF3DE', borderRadius: 8, padding: '10px 14px',
          fontSize: 13, color: '#3B6D11', marginBottom: 16
        }}>
          Next automatic run: {status.next_scheduled_run}
        </div>
      )}

      {/* Actions */}
      <div style={{
        background: '#fff', border: '1px solid #eee', borderRadius: 10,
        padding: '14px 16px', marginBottom: 16
      }}>
        <div style={{ fontWeight: 500, fontSize: 13, marginBottom: 12 }}>Trigger agents</div>

        <div style={{ display: 'flex', gap: 8 }}>
          <button
            onClick={runAll}
            disabled={running}
            // Run all users button
            style={{
                padding: '8px 16px', borderRadius: 8, border: '1px solid #ddd',
                background: running ? '#f5f5f5' : '#fff', cursor: running ? 'not-allowed' : 'pointer',
                fontSize: 13, display: 'flex', alignItems: 'center', gap: 6, color: '#333'
            }}
          >
            <i className="ti ti-player-play" style={{ fontSize: 15 }} />
            {running ? 'Running...' : 'Run all users now'}
          </button>

          <button
            onClick={loadStatus}
            // Refresh status button  
            style={{
                padding: '8px 16px', borderRadius: 8, border: '1px solid #ddd',
                background: '#fff', cursor: 'pointer', fontSize: 13,
                display: 'flex', alignItems: 'center', gap: 6, color: '#333'
            }}
          >
            <i className="ti ti-refresh" style={{ fontSize: 15 }} />
            Refresh status
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div style={{
          background: '#FCEBEB', borderRadius: 8, padding: '10px 14px',
          fontSize: 13, color: '#A32D2D', marginBottom: 16
        }}>
          {error}
        </div>
      )}

      {/* Result */}
      {result && (
        <div style={{ background: '#fff', border: '1px solid #eee', borderRadius: 10, padding: '14px 16px' }}>
          <div style={{ fontWeight: 500, fontSize: 13, marginBottom: 12 }}>Last run result</div>

          <div style={{ display: 'flex', gap: 10, marginBottom: 12 }}>
            <Stat label="run id"   value={result.run_id?.slice(-8)} />
            <Stat label="total"    value={result.total} />
            <Stat label="success"  value={result.success} />
            <Stat label="failed"   value={result.failed} />
            <Stat label="duration" value={result.duration?.toFixed(1) + 's'} />
          </div>

          {result.results?.map(r => (
            <div key={r.name} style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              padding: '8px 0', borderTop: '1px solid #f5f5f5', fontSize: 13
            }}>
              <span style={{ fontWeight: 500 }}>{r.name}</span>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                {r.score && <span style={{ color: '#888' }}>score {r.score}/100</span>}
                <Badge text={r.status} ok={r.status === 'success'} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function AgentCard({ name, role, state }) {
  const idle = state === 'IDLE'
  return (
    <div style={{
      flex: 1, background: '#fff', border: '1px solid #eee', borderRadius: 10, padding: '12px 14px'
    }}>
      <div style={{ fontWeight: 500, fontSize: 13 }}>{name}</div>
      <div style={{ fontSize: 11, color: '#888', marginBottom: 8 }}>{role}</div>
      <Badge text={state ?? '—'} ok={idle} />
    </div>
  )
}

function Stat({ label, value }) {
  return (
    <div style={{ background: '#f5f5f5', borderRadius: 8, padding: '8px 12px', flex: 1 }}>
      <div style={{ fontSize: 11, color: '#888', marginBottom: 2 }}>{label}</div>
      <div style={{ fontSize: 14, fontWeight: 500 }}>{value}</div>
    </div>
  )
}

function Badge({ text, ok }) {
  return (
    <span style={{
      fontSize: 11, padding: '2px 8px', borderRadius: 6,
      background: ok ? '#EAF3DE' : '#f5f5f5',
      color: ok ? '#3B6D11' : '#555'
    }}>{text}</span>
  )
}