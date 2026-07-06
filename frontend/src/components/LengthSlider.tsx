import React from 'react'

/** LengthSliderProps — Book Runtime range slider + No Limit toggle in the same row. */
interface LengthSliderProps {
  value: number           // page count value (50 to 750 or 9999 for No Limit)
  onChange: (value: number) => void
}

export default function LengthSlider({ value, onChange }: LengthSliderProps) {
  const isNoLimit = value >= 9999
  const sliderValue = isNoLimit ? 1000 : value

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange(parseInt(e.target.value, 10))
  }

  const handleNoLimitClick = () => {
    if (isNoLimit) {
      onChange(250) // Default back to 5 hours (250 pages) when toggled off
    } else {
      onChange(9999) // Set to No Limit
    }
  }

  const is20Plus = sliderValue >= 1000
  const displayLabel = isNoLimit 
    ? 'NO LIMIT' 
    : is20Plus 
      ? '20+ HRS' 
      : `${sliderValue / 50} ${sliderValue / 50 === 1 ? 'HR' : 'HRS'}`

  return (
    <div className="runtime-slider-row">
      <div className="range-row" style={{ flex: 1, margin: 0 }}>
        <input
          type="range"
          id="length-range"
          min={50}
          max={1000}
          step={50}
          value={sliderValue}
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
