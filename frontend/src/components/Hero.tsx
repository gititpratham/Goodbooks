/** Hero section — headline, sub-copy, and catalog stamp. */
export default function Hero() {
  return (
    <section className="hero">
      <div className="hero-grid">
        <div>
          <span className="eyebrow">No genres skipped. No guessing.</span>
          <h1 className="display">
            TELL US<br />
            WHAT YOU<br />
            <span className="accent">WANT TO READ.</span>
          </h1>
          <p className="hero-sub">
            Fill out the intake form below exactly like you'd fill out a
            library request slip. The engine cross-references your answers
            against the catalog and stamps out a shortlist — no vague "if
            you liked X" hand-waving.
          </p>
        </div>
        <div className="hero-stamp display">
          CATALOG<br />10,000+ TITLES
        </div>
      </div>
    </section>
  )
}
