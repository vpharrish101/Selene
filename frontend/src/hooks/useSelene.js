import { useState, useCallback } from 'react'

const API = ''

export function useQuery() {
  const [state, setState] = useState({ data: null, loading: false, error: null })

  const run = useCallback(async (text) => {
    setState({ data: null, loading: true, error: null })
    try {
      const res = await fetch(`${API}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: text, top_k: 5 }),
      })
      const data = await res.json()
      setState({ data, loading: false, error: null })
      return data
    } catch (e) {
      setState({ data: null, loading: false, error: e.message })
      return null
    }
  }, [])

  return { ...state, run }
}

export function useEntity() {
  const [state, setState] = useState({ data: null, loading: false, error: null })

  const fetch_ = useCallback(async (name) => {
    setState({ data: null, loading: true, error: null })
    try {
      const res = await fetch(`${API}/graph/entity/${encodeURIComponent(name)}`)
      const data = await res.json()
      setState({ data, loading: false, error: null })
      return data
    } catch (e) {
      setState({ data: null, loading: false, error: e.message })
      return null
    }
  }, [])

  return { ...state, fetch: fetch_ }
}

export function useStats() {
  const [state, setState] = useState({ data: null, loading: false, error: null })

  const fetch_ = useCallback(async () => {
    setState(s => ({ ...s, loading: true }))
    try {
      const res = await fetch(`${API}/stats`)
      const data = await res.json()
      setState({ data, loading: false, error: null })
    } catch (e) {
      setState({ data: null, loading: false, error: e.message })
    }
  }, [])

  return { ...state, fetch: fetch_ }
}

export function useGraphData() {
  const [state, setState] = useState({ data: null, loading: false, error: null })

  const fetch_ = useCallback(async () => {
    setState(s => ({ ...s, loading: true }))
    try {
      const res = await fetch(`${API}/graph/data`)
      const data = await res.json()
      setState({ data, loading: false, error: null })
      return data
    } catch (e) {
      setState({ data: null, loading: false, error: e.message })
      return null
    }
  }, [])

  return { ...state, fetch: fetch_ }
}

export async function callApi(endpoint, method = 'GET', body = null, params = {}) {
  const url = new URL(`${window.location.origin}${API}${endpoint}`)
  Object.entries(params).forEach(([k, v]) => v && url.searchParams.set(k, v))
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  }
  if (body && method !== 'GET') opts.body = JSON.stringify(body)
  const res = await fetch(url.toString(), opts)
  return res.json()
}
