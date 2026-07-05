/** LengthSlider.tsx — Page count range slider with live label. */

interface LengthSliderProps {
  value: number
  onChange: (value: number) => void
}

export default function LengthSlider({ value, onChange }: LengthSliderProps) {
  return (
    <div className="range-row">
      <input
        type="range"
        id="length-range"
        min={150}
        max={900}
        step={25}
        value={value}
        onChange={e => onChange(parseInt(e.target.value, 10))}
        aria-label="Maximum page count"
        aria-valuetext={`${value} pages`}
      />
      <span className="range-val">{value} PP</span>
    </div>
  )
}
