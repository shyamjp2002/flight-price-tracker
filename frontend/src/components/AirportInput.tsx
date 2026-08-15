import { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import type { Airport } from '../types'

interface Props {
  label: string
  value: string
  placeholder?: string
  onChange: (iata: string) => void
}

export function AirportInput({ label, value, placeholder, onChange }: Props) {
  const [query, setQuery] = useState(value)
  const [options, setOptions] = useState<Airport[]>([])
  const [open, setOpen] = useState(false)
  const wrapper = useRef<HTMLDivElement>(null)

  useEffect(() => {
    setQuery(value)
  }, [value])

  useEffect(() => {
    if (!open || query.trim().length < 2) {
      setOptions([])
      return
    }
    let cancelled = false
    const timer = setTimeout(() => {
      api
        .airports(query.trim())
        .then((found) => !cancelled && setOptions(found))
        .catch(() => !cancelled && setOptions([]))
    }, 200)
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [query, open])

  useEffect(() => {
    const onClickOutside = (event: MouseEvent) => {
      if (wrapper.current && !wrapper.current.contains(event.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [])

  const pick = (airport: Airport) => {
    onChange(airport.iata)
    setQuery(airport.iata)
    setOpen(false)
  }

  return (
    <div className="airport-input" ref={wrapper}>
      <label>
        {label}
        <input
          required
          placeholder={placeholder}
          value={query}
          autoComplete="off"
          onFocus={() => setOpen(true)}
          onChange={(event) => {
            const next = event.target.value
            setQuery(next)
            setOpen(true)
            onChange(next.length === 3 ? next.toUpperCase() : next)
          }}
        />
      </label>
      {open && options.length > 0 && (
        <ul className="airport-options">
          {options.map((airport) => (
            <li key={airport.iata}>
              <button type="button" onMouseDown={() => pick(airport)}>
                <strong>{airport.iata}</strong> {airport.city}
                <span>
                  {airport.name}, {airport.country}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
