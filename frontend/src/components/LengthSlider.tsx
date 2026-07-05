/** LengthSlider.tsx — Page count range slider. 900 = "No limit". */

interface LengthSliderProps {
  value: number
  onChange: (value: number) => void
}

export default function LengthSlider({ value, onChange }: LengthSliderProps) {
  const label = value >= 900 ? 'NO LIMIT' : `${value} PP`

  return (
    <div className="range-row">
      <input
        type="range"
        id="length-range"
        min={100}
        max={900}
        step={50}
        value={value}
        onChange={e => onChange(parseInt(e.target.value, 10))}
        aria-label="Maximum page count"
        aria-valuetext={label}
      />
      <span className="range-val">{label}</span>
    </div>
  )
}
