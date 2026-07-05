/**
 * TileGroup.tsx — Reusable multi-select or single-select tile grid.
 *
 * Props
 * -----
 * options   : list of label strings to render
 * selected  : Set<string> of currently selected values
 * onToggle  : callback when a tile is clicked
 * mode      : 'multi' = checkboxes, 'single' = radio buttons
 * group     : HTML name attribute used for accessibility
 */

interface TileGroupProps {
  options: readonly string[]
  selected: Set<string>
  onToggle: (value: string) => void
  mode: 'multi' | 'single'
  group: string
}

export default function TileGroup({
  options,
  selected,
  onToggle,
  mode,
  group,
}: TileGroupProps) {
  return (
    <div className="tiles">
      {options.map(opt => {
        const isSelected = selected.has(opt)
        return (
          <label
            key={opt}
            className={`tile${mode === 'single' ? ' radio' : ''}${isSelected ? ' selected' : ''}`}
          >
            <input
              type={mode === 'single' ? 'radio' : 'checkbox'}
              name={group}
              value={opt}
              checked={isSelected}
              onChange={() => onToggle(opt)}
              aria-label={opt}
            />
            <span className="mark" />
            {opt}
          </label>
        )
      })}
    </div>
  )
}
