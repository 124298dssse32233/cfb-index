export default function HeroFingerprint() {
  return (
    <div
      className="hero-root"
      style={{
        background: 'linear-gradient(135deg, oklch(0.18 0.01 250) 0%, oklch(0.16 0.02 260) 100%)',
        borderRadius: 'var(--radius-lg)',
        containerType: 'inline-size',
        padding: 'var(--space-12)',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Team accent gradient blob */}
      <div
        className="absolute top-0 right-0 w-96 h-96 rounded-full opacity-[0.06] blur-[120px] pointer-events-none"
        style={{ background: 'var(--team-accent)' }}
      />

      <div
        className="hero-layout-grid relative z-10"
        style={{
          display: 'grid',
          gap: 'var(--space-12)',
        }}
      >
        {/* Left: Identity */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          {/* Headshot monogram */}
          <div
            style={{
              width: '8rem',
              height: '8rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              background: 'oklch(0.25 0.01 250)',
              color: 'oklch(0.6 0.02 250)',
              fontFamily: 'var(--font-display)',
              borderRadius: 'var(--radius-md)',
              fontSize: 'var(--fs-h2)',
              fontWeight: 600,
            }}
            role="img"
            aria-label="CJ Carr, quarterback for Notre Dame"
          >
            CC
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
            {/* THE STAR - CJ CARR at display size */}
            <h1
              className="leading-none tracking-tight uppercase"
              style={{
                fontFamily: 'var(--font-display)',
                color: 'oklch(0.95 0.01 250)',
                fontWeight: 700,
                fontSize: 'var(--fs-display)',
              }}
            >
              CJ CARR
            </h1>

            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--space-2)',
                color: 'oklch(0.7 0.02 250)',
                fontSize: 'var(--fs-body)',
              }}
            >
              <span className="font-medium">Notre Dame</span>
              <span>·</span>
              <span>FBS Independents</span>
            </div>

            <div
              style={{
                display: 'flex',
                gap: 'var(--space-3)',
                marginTop: 'var(--space-2)',
                color: 'oklch(0.6 0.02 250)',
                fontSize: 'var(--fs-meta)',
              }}
            >
              <span className="font-medium">QB</span>
              <span>·</span>
              <span>Freshman</span>
              <span>·</span>
              <span>#13</span>
              <span>·</span>
              <span>6-3, 210 lb</span>
            </div>
          </div>

          {/* Current rung tag - UPDATED to HEISMAN FINALIST */}
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 'var(--space-2)',
              padding: 'var(--space-2) var(--space-4)',
              alignSelf: 'flex-start',
              fontSize: 'var(--fs-meta)',
              fontWeight: 600,
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              marginTop: 'var(--space-2)',
              background: 'oklch(0.7 0.12 85)',
              color: 'oklch(0.18 0.01 250)',
              borderRadius: '999px',
              transition: 'transform var(--motion-state), opacity var(--motion-state)',
            }}
            role="status"
            aria-label="Current player standing: Heisman Finalist"
          >
            HEISMAN FINALIST
          </div>
        </div>

        {/* Middle: The Fingerprint (5 vibe cells) */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 'var(--space-6)' }}>
          {/* CFB Index QB Score */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
            <div
              className="font-medium tracking-wider uppercase"
              style={{
                color: 'oklch(0.6 0.02 250)',
                letterSpacing: '0.08em',
                fontSize: 'var(--fs-meta)',
              }}
            >
              CFB INDEX QB SCORE
            </div>
            <div
              className="leading-none tabular-nums"
              style={{
                fontFamily: 'var(--font-display)',
                color: 'var(--percentile-90)',
                fontWeight: 700,
                fontSize: 'var(--fs-h2)',
              }}
              aria-label="CFB Index QB Score: 87 out of 100, 90th percentile among Power 4 quarterbacks"
            >
              87
            </div>
            <div className="text-sm leading-snug" style={{ color: 'oklch(0.7 0.02 250)' }}>
              Elite-tier QB. 90th pct EPA/dropback vs P4.
            </div>
          </div>

          {/* Heisman Heat */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
            <div
              className="font-medium tracking-wider uppercase"
              style={{
                color: 'oklch(0.6 0.02 250)',
                letterSpacing: '0.08em',
                fontSize: 'var(--fs-meta)',
              }}
            >
              HEISMAN HEAT
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 'var(--space-3)' }}>
              <div
                className="leading-none tabular-nums"
                style={{
                  fontFamily: 'var(--font-display)',
                  color: 'oklch(0.95 0.01 250)',
                  fontWeight: 700,
                  fontSize: 'var(--fs-h2)',
                }}
                aria-label="Heisman Trophy ranking: number 15 nowcast, trending upward"
              >
                #15
              </div>
              {/* Trajectory spark */}
              <svg width="80" height="32" className="opacity-60" aria-hidden="true">
                <polyline
                  points="0,28 16,20 32,18 48,14 64,10 80,8"
                  fill="none"
                  stroke="oklch(0.7 0.12 85)"
                  strokeWidth="2"
                  style={{
                    transition: 'stroke var(--motion-data-entry)',
                  }}
                />
                <circle cx="80" cy="8" r="3" fill="oklch(0.7 0.12 85)" />
              </svg>
            </div>
            <div className="text-sm leading-snug" style={{ color: 'oklch(0.7 0.02 250)' }}>
              2.2% win · 65.5% ballot · trending up
            </div>
          </div>

          {/* Fan Belief */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
            <div
              className="font-medium tracking-wider uppercase"
              style={{
                color: 'oklch(0.6 0.02 250)',
                letterSpacing: '0.08em',
                fontSize: 'var(--fs-meta)',
              }}
            >
              THE ROOM ON CARR
            </div>
            {/* Belief dial */}
            <div
              className="relative rounded-full overflow-hidden"
              style={{
                height: 'var(--space-3)',
                background: 'oklch(0.25 0.01 250)',
                transition: 'background var(--motion-state)',
              }}
              role="meter"
              aria-label="Fan belief meter: 72 percent, grounded optimism, based on 142 mentions with high confidence"
              aria-valuenow={72}
              aria-valuemin={0}
              aria-valuemax={100}
            >
              <div
                className="absolute inset-y-0 left-0 rounded-full"
                style={{
                  width: '72%',
                  background: 'linear-gradient(90deg, var(--belief-neutral) 0%, var(--belief-positive) 100%)',
                  transition: 'width var(--motion-data-entry)',
                }}
              />
              <div
                className="absolute top-1/2 -translate-y-1/2 rounded-sm"
                style={{
                  left: '72%',
                  width: '0.25rem',
                  height: 'var(--space-4)',
                  background: 'oklch(0.95 0.01 250)',
                  transition: 'left var(--motion-data-entry)',
                }}
              />
            </div>
            <div className="text-sm leading-snug" style={{ color: 'oklch(0.7 0.02 250)' }}>
              Grounded Optimism · 142 mentions · high confidence
            </div>
          </div>

          {/* Respect Gap */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
            <div
              className="font-medium tracking-wider uppercase"
              style={{
                color: 'oklch(0.6 0.02 250)',
                letterSpacing: '0.08em',
                fontSize: 'var(--fs-meta)',
              }}
            >
              RESPECT GAP
            </div>
            <div
              className="leading-none tabular-nums"
              style={{
                fontFamily: 'var(--font-display)',
                color: 'var(--belief-positive)',
                fontWeight: 700,
                fontSize: 'var(--fs-h2)',
              }}
              aria-label="Respect Gap: plus 12 points, fans more bullish than national consensus"
            >
              +12
            </div>
            <div className="text-sm leading-snug" style={{ color: 'oklch(0.7 0.02 250)' }}>
              Fans more bullish than national consensus
            </div>
          </div>

          {/* Reality Gap (full-width) */}
          <div style={{ gridColumn: '1 / -1', display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
            <div
              className="font-medium tracking-wider uppercase"
              style={{
                color: 'oklch(0.6 0.02 250)',
                letterSpacing: '0.08em',
                fontSize: 'var(--fs-meta)',
              }}
            >
              REALITY GAP
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 'var(--space-3)' }}>
              <div
                className="leading-none tabular-nums"
                style={{
                  fontFamily: 'var(--font-display)',
                  color: 'var(--percentile-75)',
                  fontWeight: 600,
                  fontSize: 'var(--fs-body)',
                }}
                aria-label="Reality Gap status: Aligned, fan belief matches structural model output"
              >
                ALIGNED
              </div>
              <div className="text-sm leading-snug" style={{ color: 'oklch(0.7 0.02 250)' }}>
                Fan belief matches structural model output
              </div>
            </div>
          </div>
        </div>

        {/* Right: Accolade Ribbon */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)', minWidth: '15rem' }}>
          <div
            className="font-medium tracking-wider uppercase"
            style={{
              color: 'oklch(0.6 0.02 250)',
              letterSpacing: '0.08em',
              fontSize: 'var(--fs-meta)',
              marginBottom: 'var(--space-2)',
            }}
          >
            LIVE ACCOLADES
          </div>

          {/* Heisman */}
          <div
            className="border"
            style={{
              background: 'oklch(0.20 0.01 250)',
              borderColor: 'oklch(0.28 0.01 250)',
              borderRadius: 'var(--radius-md)',
              padding: 'var(--space-4)',
              transition: 'transform var(--motion-state)',
              boxShadow: 'var(--elevation-1)',
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                justifyContent: 'space-between',
                gap: 'var(--space-2)',
                marginBottom: 'var(--space-2)',
              }}
            >
              <div className="text-sm font-semibold" style={{ color: 'oklch(0.95 0.01 250)' }}>
                Heisman Trophy
              </div>
              <svg width="40" height="20" className="opacity-60" aria-hidden="true">
                <polyline
                  points="0,16 8,14 16,12 24,10 32,8 40,6"
                  fill="none"
                  stroke="oklch(0.7 0.12 85)"
                  strokeWidth="1.5"
                />
              </svg>
            </div>
            <div
              className="leading-none tabular-nums"
              style={{
                fontFamily: 'var(--font-display)',
                color: 'oklch(0.7 0.12 85)',
                fontWeight: 600,
                fontSize: 'var(--fs-body)',
                marginBottom: 'var(--space-1)',
              }}
              aria-label="Heisman Trophy win probability: 2.2 percent, ranked number 15 in nowcast"
            >
              2.2%
            </div>
            <div style={{ color: 'oklch(0.6 0.02 250)', fontSize: 'var(--fs-meta)' }}>
              Win probability · #15 nowcast
            </div>
          </div>

          {/* Davey O'Brien */}
          <div
            className="border"
            style={{
              background: 'oklch(0.20 0.01 250)',
              borderColor: 'oklch(0.28 0.01 250)',
              borderRadius: 'var(--radius-md)',
              padding: 'var(--space-4)',
              transition: 'transform var(--motion-state)',
              boxShadow: 'var(--elevation-1)',
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                justifyContent: 'space-between',
                gap: 'var(--space-2)',
                marginBottom: 'var(--space-2)',
              }}
            >
              <div className="text-sm font-semibold" style={{ color: 'oklch(0.95 0.01 250)' }}>
                Davey O'Brien
              </div>
              <svg width="40" height="20" className="opacity-60" aria-hidden="true">
                <polyline
                  points="0,14 8,12 16,11 24,9 32,8 40,7"
                  fill="none"
                  stroke="oklch(0.7 0.12 85)"
                  strokeWidth="1.5"
                />
              </svg>
            </div>
            <div
              className="leading-none tabular-nums"
              style={{
                fontFamily: 'var(--font-display)',
                color: 'oklch(0.7 0.12 85)',
                fontWeight: 600,
                fontSize: 'var(--fs-body)',
                marginBottom: 'var(--space-1)',
              }}
              aria-label="Davey O'Brien Award win probability: 4.8 percent, ranked number 12 in nowcast"
            >
              4.8%
            </div>
            <div style={{ color: 'oklch(0.6 0.02 250)', fontSize: 'var(--fs-meta)' }}>
              Win probability · #12 nowcast
            </div>
          </div>

          {/* Consensus All-American */}
          <div
            className="border"
            style={{
              background: 'oklch(0.20 0.01 250)',
              borderColor: 'oklch(0.28 0.01 250)',
              borderRadius: 'var(--radius-md)',
              padding: 'var(--space-4)',
              transition: 'transform var(--motion-state)',
              boxShadow: 'var(--elevation-1)',
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                justifyContent: 'space-between',
                gap: 'var(--space-2)',
                marginBottom: 'var(--space-2)',
              }}
            >
              <div className="text-sm font-semibold" style={{ color: 'oklch(0.95 0.01 250)' }}>
                Consensus AA
              </div>
              <svg width="40" height="20" className="opacity-60" aria-hidden="true">
                <polyline
                  points="0,10 8,9 16,8 24,7 32,6 40,5"
                  fill="none"
                  stroke="oklch(0.7 0.12 85)"
                  strokeWidth="1.5"
                />
              </svg>
            </div>
            <div
              className="leading-none tabular-nums"
              style={{
                fontFamily: 'var(--font-display)',
                color: 'oklch(0.7 0.12 85)',
                fontWeight: 600,
                fontSize: 'var(--fs-body)',
                marginBottom: 'var(--space-1)',
              }}
              aria-label="Consensus All-American probability: 18.3 percent, requires 3 of 5 NCAA-recognized selectors"
            >
              18.3%
            </div>
            <div style={{ color: 'oklch(0.6 0.02 250)', fontSize: 'var(--fs-meta)' }}>
              3 of 5 NCAA selectors
            </div>
          </div>
        </div>
      </div>

      <style>
        {`
          /* Container query breakpoints */
          @container (min-width: 720px) {
            .hero-layout-grid {
              grid-template-columns: auto 1fr auto;
            }
          }

          /* Mobile padding reduction */
          @container (max-width: 600px) {
            .hero-root {
              padding: var(--space-6) !important;
            }
          }
        `}
      </style>
    </div>
  );
}
