import { useEffect, useId, useRef, useState } from 'react'

export type PlaceOption = {
  key: string
  label: string
  secondary?: string
}

interface PlacePickerProps {
  label: string
  placeholder: string
  value: string
  places: PlaceOption[]
  onChange: (key: string) => void
}

export function PlacePicker({
  label,
  placeholder,
  value,
  places,
  onChange,
}: PlacePickerProps) {
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)
  const listId = useId()
  const selected = places.find((place) => place.key === value) ?? null

  useEffect(() => {
    if (!open) return
    const onPointerDown = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false)
      }
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false)
    }
    document.addEventListener('pointerdown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('pointerdown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [open])

  return (
    <label className="field">
      <span>{label}</span>
      <div className="place-picker" ref={rootRef}>
        <button
          type="button"
          className={[
            'place-picker__button',
            selected ? '' : 'place-picker__button--placeholder',
          ]
            .filter(Boolean)
            .join(' ')}
          aria-label={label}
          aria-haspopup="listbox"
          aria-expanded={open}
          aria-controls={listId}
          onClick={() => setOpen((current) => !current)}
        >
          {selected ? selected.label : placeholder}
        </button>
        {open ? (
          <ul
            id={listId}
            className="place-picker__list"
            role="listbox"
            aria-label={label}
          >
            {places.map((place) => (
              <li key={place.key}>
                <button
                  type="button"
                  role="option"
                  aria-selected={place.key === value}
                  title={place.secondary}
                  className={
                    place.key === value
                      ? 'place-picker__option is-selected'
                      : 'place-picker__option'
                  }
                  onClick={() => {
                    onChange(place.key)
                    setOpen(false)
                  }}
                >
                  {place.label}
                </button>
              </li>
            ))}
          </ul>
        ) : null}
      </div>
    </label>
  )
}
