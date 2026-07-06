import React from 'react'

/** LengthSliderProps — Book Runtime range slider + No Limit toggle in the same row. */
interface LengthSliderProps {
  value: number           // page count value (50 to 750 or 9999 for No Limit)
  onChange: (value: number) => void
}

export default function LengthSlider({ value, onChange }: LengthSliderProps) {
  const RUNTIME_VALUES = [
    { hours: 10, pages: 500, label: '10 HRS' },
    { hours: 15, pages: 750, label: '15 HRS' },
    { hours: 20, pages: 1000, label: '20 HRS' },
    { hours: 30, pages: 1500, label: '30 HRS' },
    { hours: 40, pages: 2000, label: '40 HRS' }
  ]

  const isNoLimit = value >= 9999
  // Find the closest index for the current page value, default to 2 (5 hours)
  let currentIndex = RUNTIME_VALUES.findIndex(v => v.pages >= value)
  if (currentIndex === -1) currentIndex = RUNTIME_VALUES.length - 1
  if (isNoLimit) currentIndex = RUNTIME_VALUES.length - 1 // Default visual position when No Limit is toggled

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const idx = parseInt(e.target.value, 10)
    onChange(RUNTIME_VALUES[idx].pages)
  }

  const handleNoLimitClick = () => {
    if (isNoLimit) {
      onChange(250) // Default back to 5 hours (250 pages) when toggled off
    } else {
      onChange(9999) // Set to No Limit
    }
  }

  const displayLabel = isNoLimit 
    ? 'NO LIMIT' 
    : RUNTIME_VALUES[currentIndex].label

  return (
    <div className="runtime-slider-row">
      <div className="range-row" style={{ flex: 1, margin: 0 }}>
        <input
          type="range"
          id="length-range"
          min={0}
          max={RUNTIME_VALUES.length - 1}
          step={1}
          value={currentIndex}
          onChange={handleSliderChange}
          disabled={isNoLimit}
          aria-label="Maximum book runtime"
          aria-valuetext={displayLabel}
          style={{ opacity: isNoLimit ? 0.5 : 1, transition: 'opacity 0.2s' }}
        />
        <span className="range-val" style={{ minWidth: '110px', textAlign: 'right' }}>
          {displayLabel}
        </span>
      </div>
      <button
        type="button"
        className={`tile${isNoLimit ? ' selected' : ''}`}
        onClick={handleNoLimitClick}
        style={{
          margin: 0,
          whiteSpace: 'nowrap',
          padding: '12px 20px',
          height: '58px', // match the range-row box height exactly
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        No Limit
      </button>
    </div>
  )
}
