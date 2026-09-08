import { useId } from 'react'

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
  const selectId = useId()

  return (
    <label className="field" htmlFor={selectId}>
      <span>{label}</span>
      <div className="place-picker">
        <select
          id={selectId}
          name={label}
          aria-label={label}
          required
          value={value}
          onChange={(event) => onChange(event.target.value)}
        >
          <option value="">{placeholder}</option>
          {places.map((place) => (
            <option key={place.key} value={place.key} title={place.secondary}>
              {place.label}
            </option>
          ))}
        </select>
        <span className="place-picker__chevron" aria-hidden="true">
          ▾
        </span>
      </div>
    </label>
  )
}
