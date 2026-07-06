/** Hero section — headline, sub-copy, and catalog stamp. */
export default function Hero() {
  return (
    <section className="hero">
      <div className="hero-grid">
        <div>
          <span className="eyebrow">No genres skipped. No guessing.</span>
          <h1 className="display">
            GET THE<br />
            BEST BOOK<br />
            <span className="accent">RECOMMENDED.</span>
          </h1>
          <p className="hero-sub">
            Fill out the intake form below exactly like you'd fill out a
            library request slip. The engine cross-references your answers
            against the catalog and stamps out a shortlist. <strong style={{ fontWeight: 500 }}>Personalized recommendations to help you find your next great read.</strong>
          </p>
        </div>
        <div className="hero-stamp display">
          CATALOG<br />10,000+ TITLES
        </div>
      </div>
    </section>
  )
}
