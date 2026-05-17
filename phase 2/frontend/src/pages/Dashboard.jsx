import { useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { api } from '../api'

const card = { background: '#f5f5f5', borderRadius: 8, padding: '12px 14px', flex: 1 }
const td   = { padding: '7px 8px', borderBottom: '1px solid #f5f5f5', color: '#333' }

export default function Dashboard() {
  const [status,  setStatus]  = useState(null)
  const [history, setHistory] = useState(null)
  const [runs,    setRuns]    = useState([])
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)

  useEffect(() => { load() }, [])

  async function load() {
    try {
      setLoading(true)
      const s = await api.getStatus()
      setStatus(s)
      const r = await api.getSchedulerRuns()
      setRuns(r || [])
      try {
        const h = await api.getAllHistory()
        setHistory(h)
      } catch {
        setHistory(null)
      }
    } catch (e) {
      setError('Could not connect to agent backend.')
    } finally {
      setLoading(false)
    }
  }

  if (loading) return <Loader />
  if (error)   return <Error msg={error} />

  const firstUser   = Object.keys(history || {})[0]
  const userHistory = firstUser ? history[firstUser] : null

  const avgScore = userHistory?.runs?.length
    ? Math.round(userHistory.runs.reduce((a, r) => a + r.plan_score, 0) / userHistory.runs.length)
    : 0

  const totalSuccess = (runs || []).reduce((a, r) => a + (r.success || 0), 0)
  const lastRun      = runs?.[0]
  const lastDuration = lastRun?.finished_at && lastRun?.started_at
    ? ((new Date(lastRun.finished_at) - new Date(lastRun.started_at)) / 1000).toFixed(1) + 's'
    : '—'

  const chartData = userHistory?.runs?.map((r, i) => ({
    label: `Run ${i + 1}`,
    score: r.plan_score ?? 0,
  })) ?? []

  const trend = userHistory?.trend

  return (
    <div style={{ padding: 20 }}>
    
        {/* Description */}
        <div style={{
        background: '#fff', border: '1px solid #eee', borderRadius: 10,
        padding: '14px 16px', marginBottom: 16
        }}>
        <div style={{ fontWeight: 500, fontSize: 13, marginBottom: 6 }}>
            What this system does
        </div>
        <div style={{ fontSize: 13, color: '#555', lineHeight: 1.7, textAlign: 'left' }}>
            Three autonomous agents work together to manage your finances.
            <strong style={{ color: '#111' }}> Agent 1</strong> reads your salary profile, checks every expense
            against the 50/30/20 rule, and calls GPT to write personalised recommendations.
            <strong style={{ color: '#111' }}> Agent 2</strong> picks up the plan, decides which actions to take,
            and sends budget alerts and a monthly summary to your email.
            <strong style={{ color: '#111' }}> Agent 3</strong> runs everything automatically on the 1st of every
            month — no human trigger needed.
        </div>
        </div>

      {/* Summary cards */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 16 }}>
        <StatCard label="total users"  value={status?.profiles?.length ?? 0} sub="profiles stored" />
        <StatCard label="avg score"    value={avgScore}     sub="out of 100" />
        <StatCard label="total runs"   value={totalSuccess} sub="successful" />
        <StatCard label="last run"     value={lastDuration} sub={lastRun?.started_at ? lastRun.started_at.slice(0, 10) : '—'} />
      </div>

      {/* Trend alert */}
      {trend && (
        <div style={{
          background: trend.direction === 'improving' ? '#EAF3DE'
                    : trend.direction === 'declining' ? '#FCEBEB' : '#f5f5f5',
          borderRadius: 8, padding: '10px 14px', marginBottom: 16, fontSize: 13,
          color: trend.direction === 'improving' ? '#3B6D11'
               : trend.direction === 'declining' ? '#A32D2D' : '#555'
        }}>
          {trend.direction === 'improving' && `▲ Score improved by ${trend.score_delta} points vs last run`}
          {trend.direction === 'declining' && `▼ Score dropped by ${Math.abs(trend.score_delta)} points vs last run`}
          {trend.direction === 'stable'    && `→ Score stable vs last run — no change`}
        </div>
      )}

      {/* Chart */}
      {chartData.length > 0 && (
        <div style={{ background: '#fff', border: '1px solid #eee', borderRadius: 10, padding: '14px 16px', marginBottom: 16 }}>
          <div style={{ fontWeight: 500, fontSize: 13, marginBottom: 12 }}>
            Score trend — {firstUser}
          </div>
          <ResponsiveContainer width="100%" height={140}>
            <BarChart data={chartData} barSize={28}>
              <XAxis dataKey="label" tick={{ fontSize: 11, fill: '#888' }} axisLine={false} tickLine={false} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: '#888' }} axisLine={false} tickLine={false} width={28} />
              <Tooltip
                contentStyle={{ fontSize: 12, borderRadius: 6, border: '1px solid #eee' }}
                formatter={(v) => [v + '/100', 'Score']}
              />
              <Bar dataKey="score" radius={[4, 4, 0, 0]}>
                {chartData.map((d, i) => (
                  <Cell key={i} fill={d.score >= 80 ? '#1D9E75' : d.score >= 60 ? '#BA7517' : '#E24B4A'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Recent plans */}
      {userHistory?.runs?.length > 0 && (
        <div style={{ background: '#fff', border: '1px solid #eee', borderRadius: 10, padding: '14px 16px' }}>
          <div style={{ fontWeight: 500, fontSize: 13, marginBottom: 12 }}>Recent plans</div>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr>
                {['User', 'Score', 'Savings', 'Expenses', 'Status', 'Date'].map(h => (
                  <th key={h} style={{ textAlign: 'left', padding: '4px 8px', fontSize: 11, color: '#888', borderBottom: '1px solid #eee' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {userHistory.runs.slice().reverse().map(r => (
                <tr key={r.id}>
                  <td style={td}>{firstUser}</td>
                  <td style={td}>
                    <span style={{ fontWeight: 500, color: r.plan_score >= 80 ? '#1D9E75' : r.plan_score >= 60 ? '#BA7517' : '#E24B4A' }}>
                      {r.plan_score}/100
                    </span>
                  </td>
                  <td style={td}>₹{r.current_savings?.toLocaleString() ?? '—'}</td>
                  <td style={td}>₹{r.total_expenses?.toLocaleString() ?? '—'}</td>
                  <td style={td}><Badge text={r.status} ok={r.status === 'executed'} /></td>
                  <td style={td}>{r.created_at ? r.created_at.slice(0, 10) : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!userHistory && !loading && (
        <div style={{ textAlign: 'center', padding: 40, color: '#888', fontSize: 13 }}>
          No plans yet. Run the scheduler to see data here.
        </div>
      )}
    </div>
  )
}

function StatCard({ label, value, sub }) {
  return (
    <div style={card}>
      <div style={{ fontSize: 11, color: '#888', marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 500 }}>{value}</div>
      <div style={{ fontSize: 11, color: '#888', marginTop: 2 }}>{sub}</div>
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

function Loader() {
  return <div style={{ padding: 40, textAlign: 'center', color: '#888', fontSize: 13 }}>Loading...</div>
}

function Error({ msg }) {
  return <div style={{ padding: 40, textAlign: 'center', color: '#A32D2D', fontSize: 13 }}>{msg}</div>
}