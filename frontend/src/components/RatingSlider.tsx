/** RatingSlider.tsx — Minimum average rating slider (1.0 – 5.0, step 0.5). */

interface RatingSliderProps {
  value: number
  onChange: (value: number) => void
}

export default function RatingSlider({ value, onChange }: RatingSliderProps) {
  const stars = '★'.repeat(Math.round(value)) + '☆'.repeat(5 - Math.round(value))

  return (
    <div className="range-row">
      <input
        type="range"
        id="rating-range"
        min={1}
        max={5}
        step={0.5}
        value={value}
        onChange={e => onChange(parseFloat(e.target.value))}
        aria-label="Minimum average rating"
        aria-valuetext={`${value} stars`}
      />
      <span className="range-val">{value.toFixed(1)} {stars}</span>
    </div>
  )
}
