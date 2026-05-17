import { useEffect, useState } from 'react'
import { api } from '../api'

const LEVEL_COLOR = { info: '#555', warn: '#BA7517', error: '#A32D2D' }

export default function AgentLogs() {
  const [logs,    setLogs]    = useState([])
  const [filter,  setFilter]  = useState('all')
  const [loading, setLoading] = useState(true)

  useEffect(() => { load() }, [])

  async function load() {
    try {
      const data = await api.getLogs()
      setLogs(data.entries || [])
    } catch { setLogs([]) }
    finally { setLoading(false) }
  }

  const filtered = filter === 'all'
    ? logs
    : logs.filter(l => l.level === filter)

  if (loading) return <Loader />

  return (
    <div style={{ padding: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <div style={{ fontWeight: 500, fontSize: 13 }}>
          Agent 1 decision log — {logs.length} entries
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          {['all', 'info', 'warn', 'error'].map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              style={{
                fontSize: 12, padding: '4px 10px', borderRadius: 6,
                border: '1px solid #ddd', cursor: 'pointer',
                background: filter === f ? '#f5f5f5' : '#fff',
                fontWeight: filter === f ? 500 : 400,
                color: f === 'warn' ? '#BA7517' : f === 'error' ? '#A32D2D' : '#555'
              }}
            >
              {f}
            </button>
          ))}
          <button
            onClick={load}
            style={{
              fontSize: 12, padding: '4px 10px', borderRadius: 6,
              border: '1px solid #ddd', cursor: 'pointer', background: '#fff',
              display: 'flex', alignItems: 'center', gap: 4
            }}
          >
            <i className="ti ti-refresh" style={{ fontSize: 13 }} /> Refresh
          </button>
        </div>
      </div>

      <div style={{
        background: '#fff', border: '1px solid #eee', borderRadius: 10,
        padding: '12px 14px', fontFamily: 'monospace'
      }}>
        {filtered.length === 0 && (
          <div style={{ fontSize: 12, color: '#aaa', padding: '20px 0', textAlign: 'center' }}>
            No log entries. Run the agent first.
          </div>
        )}
        {filtered.map((l, i) => (
          <div key={i} style={{
            display: 'flex', gap: 12, fontSize: 12, lineHeight: '1.8',
            borderBottom: i < filtered.length - 1 ? '1px solid #f9f9f9' : 'none',
            padding: '1px 0'
          }}>
            <span style={{
              minWidth: 80, color: '#1D9E75', flexShrink: 0
            }}>{l.state}</span>
            <span style={{
              minWidth: 40, color: LEVEL_COLOR[l.level] || '#555',
              textTransform: 'uppercase', fontSize: 10, paddingTop: 2, flexShrink: 0
            }}>{l.level}</span>
            <span style={{ color: '#333' }}>{l.message}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function Loader() {
  return <div style={{ padding: 40, textAlign: 'center', color: '#888', fontSize: 13 }}>Loading...</div>
}