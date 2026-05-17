import { useEffect, useState } from 'react'
import { api } from '../api'

export default function RunHistory() {
  const [runs,     setRuns]     = useState([])
  const [selected, setSelected] = useState(null)
  const [jobs,     setJobs]     = useState(null)
  const [loading,  setLoading]  = useState(true)

  useEffect(() => { load() }, [])

  async function load() {
    try {
      const r = await api.getSchedulerRuns()
      setRuns(r)
    } catch { setRuns([]) }
    finally { setLoading(false) }
  }

  async function loadDetail(runId) {
    setSelected(runId)
    try {
      const d = await api.getRunDetail(runId)
      setJobs(d.jobs)
    } catch { setJobs([]) }
  }

  if (loading) return <Loader />

  return (
    <div style={{ padding: 20, display: 'flex', gap: 16 }}>

      {/* Run list */}
      <div style={{ width: 260, flexShrink: 0 }}>
        <div style={{ fontWeight: 500, fontSize: 13, marginBottom: 10 }}>Scheduler runs</div>
        {runs.length === 0 && (
          <div style={{ fontSize: 12, color: '#aaa' }}>No runs yet</div>
        )}
        {runs.map(r => {
          const dur = ((new Date(r.finished_at) - new Date(r.started_at)) / 1000).toFixed(1)
          return (
            <div
              key={r.run_id}
              onClick={() => loadDetail(r.run_id)}
              style={{
                padding: '10px 12px', borderRadius: 8, cursor: 'pointer', marginBottom: 6,
                background: selected === r.run_id ? '#f5f5f5' : '#fff',
                border: '1px solid #eee', fontSize: 13
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
                <span style={{ fontFamily: 'monospace', fontSize: 11, color: '#888' }}>
                  {r.run_id?.slice(-12)}
                </span>
                <span style={{ fontSize: 11, color: '#888' }}>{dur}s</span>
              </div>
              <div style={{ display: 'flex', gap: 6 }}>
                <Badge text={`${r.success} ok`}   ok={true} />
                {r.failed > 0 && <Badge text={`${r.failed} failed`} ok={false} />}
              </div>
              <div style={{ fontSize: 11, color: '#aaa', marginTop: 3 }}>
                {r.started_at?.slice(0, 16).replace('T', ' ')}
              </div>
            </div>
          )
        })}
      </div>

      {/* Job detail */}
      <div style={{ flex: 1 }}>
        {jobs && (
          <div style={{ background: '#fff', border: '1px solid #eee', borderRadius: 10, padding: 16 }}>
            <div style={{ fontWeight: 500, fontSize: 13, marginBottom: 12 }}>
              Job detail — {selected?.slice(-12)}
            </div>
            {jobs.map(j => (
              <div key={j.id} style={{
                padding: '10px 0', borderBottom: '1px solid #f5f5f5', fontSize: 13
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                  <span style={{ fontWeight: 500 }}>{j.name}</span>
                  <Badge text={j.status} ok={j.status === 'success'} />
                </div>
                {j.plan_id && (
                  <div style={{ fontSize: 12, color: '#888' }}>plan id: {j.plan_id}</div>
                )}
                {j.error && (
                  <div style={{ fontSize: 12, color: '#A32D2D', marginTop: 4 }}>{j.error}</div>
                )}
                <div style={{ fontSize: 11, color: '#aaa', marginTop: 2 }}>
                  {j.started_at?.slice(0, 16).replace('T', ' ')} →{' '}
                  {j.finished_at?.slice(11, 19)}
                </div>
              </div>
            ))}
          </div>
        )}
        {!jobs && (
          <div style={{ textAlign: 'center', padding: 40, color: '#aaa', fontSize: 13 }}>
            Select a run to see per-user job details
          </div>
        )}
      </div>
    </div>
  )
}

function Badge({ text, ok }) {
  return (
    <span style={{
      fontSize: 11, padding: '2px 8px', borderRadius: 6,
      background: ok ? '#EAF3DE' : '#FCEBEB',
      color: ok ? '#3B6D11' : '#A32D2D'
    }}>{text}</span>
  )
}

function Loader() {
  return <div style={{ padding: 40, textAlign: 'center', color: '#888', fontSize: 13 }}>Loading...</div>
}