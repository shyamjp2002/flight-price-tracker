import { useCallback, useEffect, useState } from 'react'
import './App.css'
import { api } from './api'
import { WatchCard } from './components/WatchCard'
import { WatchForm } from './components/WatchForm'
import type { Alert, Watch, WatchInput } from './types'

export default function App() {
  const [watches, setWatches] = useState<Watch[]>([])
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [provider, setProvider] = useState('')
  const [error, setError] = useState('')
  const [checkingAll, setCheckingAll] = useState(false)

  const refresh = useCallback(async () => {
    try {
      const [nextWatches, nextAlerts, health] = await Promise.all([
        api.listWatches(),
        api.alerts(),
        fetch('/api/health').then((response) => response.json()),
      ])
      setWatches(nextWatches)
      setAlerts(nextAlerts)
      setProvider(health.provider)
      setError('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'cannot reach the API')
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const create = async (payload: WatchInput) => {
    await api.createWatch(payload)
    await refresh()
  }

  const checkAll = async () => {
    setCheckingAll(true)
    try {
      await api.checkAll()
      await refresh()
    } finally {
      setCheckingAll(false)
    }
  }

  return (
    <main>
      <header className="page-header">
        <div>
          <h1>Flight Price Tracker</h1>
          <p className="muted">
            Watch a route, poll the cheapest fare, get alerted when it drops. Provider:{' '}
            <code>{provider || '…'}</code>
          </p>
        </div>
        <button onClick={checkAll} disabled={checkingAll || watches.length === 0}>
          {checkingAll ? 'Checking…' : 'Check all now'}
        </button>
      </header>

      {error && <p className="card error">{error}</p>}

      <WatchForm onCreate={create} />

      <section className="watches">
        {watches.length === 0 ? (
          <p className="card muted">No watches yet. Add a route above.</p>
        ) : (
          watches.map((watch) => (
            <WatchCard key={watch.id} watch={watch} onChanged={refresh} />
          ))
        )}
      </section>

      {alerts.length > 0 && (
        <section className="card alerts">
          <h2>Alerts</h2>
          <ul>
            {alerts.map((alert) => (
              <li key={alert.id}>
                <span className="muted">{alert.created_at}</span> {alert.message}
              </li>
            ))}
          </ul>
        </section>
      )}
    </main>
  )
}
