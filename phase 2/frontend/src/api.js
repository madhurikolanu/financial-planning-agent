import axios from 'axios'

const http = axios.create({ baseURL: '/api' })

export const api = {

  // ── System ──────────────────────────────────────────
  getStatus: () =>
    http.get('/status').then(r => r.data),

  // ── Profiles ────────────────────────────────────────
  getProfiles: () =>
    http.get('/status').then(r => r.data.profiles),

  getProfile: (name) =>
    http.get(`/profile/${name}`).then(r => r.data),

  saveProfile: (data) =>
    http.post('/profile', data).then(r => r.data),

  // ── Analysis ────────────────────────────────────────
  analyzeUser: (name) =>
    http.post(`/analyze/${name}`).then(r => r.data),

  getAllHistory: () =>
    http.get('/history').then(r => r.data),

  getHistory: (name) =>
    http.get(`/history/${name}`).then(r => r.data),

  getActions: (planId) =>
    http.get(`/actions/${planId}`).then(r => r.data),

  // ── Scheduler ────────────────────────────────────────
  runScheduler: () =>
    http.post('/scheduler/run').then(r => r.data),

  getSchedulerStatus: () =>
    http.get('/scheduler/status').then(r => r.data),

  getSchedulerRuns: () =>
    http.get('/scheduler/runs').then(r => r.data),

  getRunDetail: (runId) =>
    http.get(`/scheduler/runs/${runId}`).then(r => r.data),

  // ── Logs ─────────────────────────────────────────────
  getLogs: () =>
    http.get('/logs').then(r => r.data),

  getAgent2Logs: () =>
    http.get('/logs/agent2').then(r => r.data),

  getAgent3Logs: () =>
    http.get('/logs/agent3').then(r => r.data),
}