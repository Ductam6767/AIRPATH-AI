import { useEffect, useId, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useI18n } from '../i18n/LanguageContext'

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
  const { t } = useI18n()
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)
  const listId = useId()
  const selected = places.find((place) => place.key === value) ?? null

  useEffect(() => {
    if (!open) return
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false)
    }
    document.addEventListener('keydown', onKeyDown)
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKeyDown)
      document.body.style.overflow = previousOverflow
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
          aria-haspopup="dialog"
          aria-expanded={open}
          onClick={() => setOpen(true)}
        >
          <span className="place-picker__value">
            {selected ? selected.label : placeholder}
          </span>
          <span className="place-picker__chevron" aria-hidden="true">
            ▾
          </span>
        </button>
        {open
          ? createPortal(
              <div
                className="place-picker-overlay"
                role="presentation"
                onClick={() => setOpen(false)}
              >
                <div
                  className="place-picker-overlay__panel"
                  role="dialog"
                  aria-label={label}
                  onClick={(event) => event.stopPropagation()}
                >
                  <div className="place-picker-overlay__head">
                    <strong>{label}</strong>
                    <button
                      type="button"
                      className="place-picker-overlay__close"
                      onClick={() => setOpen(false)}
                    >
                      {t.close}
                    </button>
                  </div>
                  <ul
                    id={listId}
                    className="place-picker-overlay__list"
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
                </div>
              </div>,
              document.body,
            )
          : null}
      </div>
    </label>
  )
}
