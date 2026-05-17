import { useEffect, useState } from 'react'
import { api } from '../api'

const input = {
  width: '100%', padding: '8px 10px', borderRadius: 8,
  border: '1px solid #ddd', fontSize: 13, marginBottom: 8,
  outline: 'none', background: '#fff', color: '#111'
}

export default function Profiles() {
  const [profiles,  setProfiles]  = useState([])
  const [selected,  setSelected]  = useState(null)
  const [form,      setForm]      = useState(null)
  const [saving,    setSaving]    = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [liveLogs,  setLiveLogs]  = useState([])
  const [msg,       setMsg]       = useState(null)

  useEffect(() => { loadProfiles() }, [])

  async function loadProfiles() {
    try {
      const s = await api.getStatus()
      setProfiles(s.profiles || [])
    } catch {}
  }

  async function loadProfile(name) {
    try {
      const p = await api.getProfile(name)
      setSelected(p)
      setForm(null)
      setLiveLogs([])
      setMsg(null)
    } catch {}
  }

  function startNew() {
    setSelected(null)
    setLiveLogs([])
    setMsg(null)
    setForm({
      name: '', email: '', monthly_salary: '',
      expenses: {
        housing: '', food: '', transport: '',
        utilities: '', entertainment: '', miscellaneous: ''
      }
    })
  }

  function editProfile(p) {
    setLiveLogs([])
    setMsg(null)
    setForm({
      name: p.name, email: p.email || '',
      monthly_salary: p.monthly_salary,
      expenses: p.expenses
    })
  }

  async function save() {
    setSaving(true)
    setMsg(null)
    try {
      await api.saveProfile({
        ...form,
        monthly_salary: parseFloat(form.monthly_salary),
        expenses: Object.fromEntries(
          Object.entries(form.expenses).map(([k, v]) => [k, parseFloat(v)])
        )
      })
      setMsg({ ok: true, text: `Profile saved for '${form.name}'` })
      setForm(null)
      await loadProfiles()
    } catch (e) {
      setMsg({ ok: false, text: e.response?.data?.detail || 'Save failed' })
    } finally {
      setSaving(false)
    }
  }

  async function analyzeNow(name) {
    setAnalyzing(true)
    setLiveLogs([])
    setMsg(null)

    const poller = setInterval(async () => {
      try {
        const data = await api.getLogs()
        setLiveLogs(data.entries || [])
      } catch {}
    }, 1000)

    try {
      const plan = await api.analyzeUser(name)
      const data = await api.getLogs()
      setLiveLogs(data.entries || [])
      setMsg({ ok: true, text: `Plan ready for '${name}' — score ${plan.plan_score}/100` })
    } catch (e) {
      setMsg({ ok: false, text: e.response?.data?.detail || 'Analysis failed' })
    } finally {
      clearInterval(poller)
      setAnalyzing(false)
    }
  }

  return (
    <div style={{ padding: 20, display: 'flex', gap: 16 }}>

      {/* Left: profile list */}
      <div style={{ width: 200, flexShrink: 0 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
          <span style={{ fontWeight: 500, fontSize: 13, color: '#111' }}>Users</span>
          <button onClick={startNew} style={{
            fontSize: 12, padding: '4px 10px', borderRadius: 6,
            border: '1px solid #ddd', background: '#fff', cursor: 'pointer',
            display: 'flex', alignItems: 'center', gap: 4, color: '#333'
          }}>
            <i className="ti ti-plus" style={{ fontSize: 14 }} /> Add
          </button>
        </div>

        {profiles.map(name => (
          <div
            key={name}
            onClick={() => loadProfile(name)}
            style={{
              padding: '8px 10px', borderRadius: 8, cursor: 'pointer', fontSize: 13,
              background: selected?.name === name ? '#f5f5f5' : 'transparent',
              fontWeight: selected?.name === name ? 500 : 400,
              color: selected?.name === name ? '#111' : '#555',
              display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2
            }}
          >
            <i className="ti ti-user" style={{ fontSize: 14, color: '#888' }} />
            {name}
          </div>
        ))}

        {profiles.length === 0 && (
          <div style={{ fontSize: 12, color: '#aaa', padding: '8px 0' }}>No profiles yet</div>
        )}
      </div>

      {/* Right: profile detail or form */}
      <div style={{ flex: 1 }}>

        {msg && (
          <div style={{
            background: msg.ok ? '#EAF3DE' : '#FCEBEB',
            color: msg.ok ? '#3B6D11' : '#A32D2D',
            borderRadius: 8, padding: '8px 12px', fontSize: 13, marginBottom: 12
          }}>
            {msg.text}
          </div>
        )}

        {/* View mode */}
        {selected && !form && (
          <div style={{ background: '#fff', border: '1px solid #eee', borderRadius: 10, padding: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
              <div>
                <div style={{ fontWeight: 500, fontSize: 15, color: '#111' }}>{selected.name}</div>
                <div style={{ fontSize: 12, color: '#888' }}>{selected.email || 'no email'}</div>
              </div>
              <div style={{ display: 'flex', gap: 6 }}>
                <button onClick={() => editProfile(selected)} style={{
                  fontSize: 12, padding: '5px 12px', borderRadius: 6,
                  border: '1px solid #ddd', background: '#fff', cursor: 'pointer', color: '#333'
                }}>
                  <i className="ti ti-edit" style={{ fontSize: 14 }} /> Edit
                </button>
                <button onClick={() => analyzeNow(selected.name)} disabled={analyzing} style={{
                  fontSize: 12, padding: '5px 12px', borderRadius: 6,
                  border: '1px solid #1D9E75',
                  background: analyzing ? '#f5f5f5' : '#EAF3DE',
                  cursor: analyzing ? 'not-allowed' : 'pointer', color: '#3B6D11'
                }}>
                  <i className="ti ti-player-play" style={{ fontSize: 14 }} />
                  {analyzing ? ' Running...' : ' Analyze now'}
                </button>
              </div>
            </div>

            <div style={{ fontSize: 13, marginBottom: 8 }}>
              <span style={{ color: '#888' }}>Monthly salary: </span>
              <span style={{ fontWeight: 500 }}>₹{selected.monthly_salary?.toLocaleString()}</span>
            </div>

            <div style={{ borderTop: '1px solid #f5f5f5', paddingTop: 12 }}>
              <div style={{ fontSize: 12, color: '#888', marginBottom: 8 }}>Expenses</div>
              {Object.entries(selected.expenses || {}).map(([k, v]) => (
                <div key={k} style={{
                  display: 'flex', justifyContent: 'space-between',
                  fontSize: 13, padding: '4px 0', borderBottom: '1px solid #f5f5f5'
                }}>
                  <span style={{ color: '#555', textTransform: 'capitalize' }}>{k}</span>
                  <span style={{ fontWeight: 500 }}>₹{v?.toLocaleString()}</span>
                </div>
              ))}
            </div>

            {/* Live agent log */}
            {liveLogs.length > 0 && (
              <div style={{ marginTop: 16 }}>
                <div style={{ fontSize: 12, color: '#888', marginBottom: 6, fontWeight: 500 }}>
                  Agent decision log
                </div>
                <div style={{
                  background: '#fafafa', border: '1px solid #eee', borderRadius: 8,
                  padding: '10px 12px', maxHeight: 200, overflowY: 'auto',
                  fontFamily: 'monospace'
                }}>
                  {liveLogs.map((l, i) => (
                    <div key={i} style={{
                      fontSize: 11, lineHeight: 1.8,
                      color: l.level === 'warn'  ? '#BA7517'
                           : l.level === 'error' ? '#A32D2D'
                           : '#555'
                    }}>
                      <span style={{ color: '#1D9E75', marginRight: 8 }}>{l.state}</span>
                      <span style={{ color: '#aaa', marginRight: 8, textTransform: 'uppercase', fontSize: 10 }}>
                        {l.level}
                      </span>
                      {l.message}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Edit / new form */}
        {form && (
          <div style={{ background: '#fff', border: '1px solid #eee', borderRadius: 10, padding: 16 }}>
            <div style={{ fontWeight: 500, fontSize: 13, marginBottom: 12, color: '#111' }}>
              {form.name ? `Edit — ${form.name}` : 'New profile'}
            </div>

            <input
              style={input} placeholder="Name" value={form.name}
              onChange={e => setForm({ ...form, name: e.target.value })}
            />
            <input
              style={input} placeholder="Email" value={form.email}
              onChange={e => setForm({ ...form, email: e.target.value })}
            />
            <input
              style={input} placeholder="Monthly salary (₹)" type="number"
              value={form.monthly_salary}
              onChange={e => setForm({ ...form, monthly_salary: e.target.value })}
            />

            <div style={{ fontSize: 12, color: '#888', margin: '8px 0 4px' }}>Expenses (₹)</div>
            {Object.keys(form.expenses).map(k => (
              <input
                key={k} style={input}
                placeholder={k.charAt(0).toUpperCase() + k.slice(1)}
                type="number" value={form.expenses[k]}
                onChange={e => setForm({
                  ...form, expenses: { ...form.expenses, [k]: e.target.value }
                })}
              />
            ))}

            <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
              <button onClick={save} disabled={saving} style={{
                flex: 1, padding: '8px', borderRadius: 8, border: '1px solid #ddd',
                background: '#fff', cursor: saving ? 'not-allowed' : 'pointer',
                fontSize: 13, color: '#333'
              }}>
                {saving ? 'Saving...' : 'Save profile'}
              </button>
              <button onClick={() => setForm(null)} style={{
                padding: '8px 14px', borderRadius: 8, border: '1px solid #ddd',
                background: '#fff', cursor: 'pointer', fontSize: 13, color: '#333'
              }}>
                Cancel
              </button>
            </div>
          </div>
        )}

        {!selected && !form && (
          <div style={{ textAlign: 'center', padding: 40, color: '#aaa', fontSize: 13 }}>
            Select a user or add a new profile
          </div>
        )}
      </div>
    </div>
  )
}