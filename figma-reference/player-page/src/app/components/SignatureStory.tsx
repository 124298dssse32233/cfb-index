// Signature Story — 5m tier
// One statistical fingerprint that defines this player's season

type StateVariant = 'full' | 'empty' | 'loading' | 'partial' | 'error';

export default function SignatureStory({ variant = 'full' }: { variant?: StateVariant }) {
  // For CJ Carr: pressure performance signature
  const story = {
    headline: 'Best QB in football under pressure',
    stat: {
      value: '0.38',
      unit: 'EPA/dropback',
      context: 'when blitzed',
    },
    rank: {
      national: 1,
      percentile: 92,
    },
    narrative:
      "When defenses bring five or more rushers, Carr doesn't flinch — he climbs the pocket, resets his feet, and delivers strikes downfield. His 0.38 EPA per dropback under pressure ranks #1 nationally and lands him in the 92nd percentile vs all P4 quarterbacks. This isn't just composure; it's a measurable edge that separates elite from good.",
    cohortComparison: [
      { label: 'CJ Carr', value: 0.38, color: 'var(--percentile-100)' },
      { label: 'P4 Avg', value: 0.12, color: 'var(--percentile-50)' },
      { label: 'Top 10', value: 0.29, color: 'var(--percentile-90)' },
    ],
    weeklyData: [
      { week: 1, value: 0.22 },
      { week: 2, value: 0.31 },
      { week: 3, value: 0.28 },
      { week: 4, value: 0.35 },
      { week: 5, value: 0.41 },
      { week: 6, value: 0.44 },
      { week: 7, value: 0.39 },
      { week: 8, value: 0.42 },
      { week: 9, value: 0.38 },
      { week: 10, value: 0.45 },
      { week: 11, value: 0.38 },
    ],
  };

  const maxValue = Math.max(...story.weeklyData.map((d) => d.value), ...story.cohortComparison.map((c) => c.value));

  // Empty state
  if (variant === 'empty') {
    return (
      <div
        className="border"
        style={{
          background: 'oklch(0.18 0.01 250)',
          borderColor: 'oklch(0.25 0.01 250)',
          borderRadius: 'var(--radius-lg)',
          containerType: 'inline-size',
          padding: 'var(--space-12)',
        }}
      >
        <div style={{ marginBottom: 'var(--space-8)' }}>
          <div
            className="font-medium tracking-wider uppercase"
            style={{
              color: 'oklch(0.6 0.02 250)',
              letterSpacing: '0.08em',
              fontSize: 'var(--fs-meta)',
              marginBottom: 'var(--space-2)',
            }}
          >
            SIGNATURE STORY
          </div>
          <h2
            className="leading-tight"
            style={{
              fontFamily: 'var(--font-display)',
              color: 'oklch(0.95 0.01 250)',
              fontWeight: 600,
              fontSize: 'var(--fs-h1)',
            }}
          >
            Awaiting candidate metric
          </h2>
        </div>
        <div
          className="border"
          style={{
            padding: 'var(--space-6)',
            background: 'oklch(0.20 0.01 250)',
            borderColor: 'oklch(0.28 0.01 250)',
            borderRadius: 'var(--radius-md)',
          }}
        >
          <p className="text-sm leading-relaxed" style={{ color: 'oklch(0.7 0.02 250)' }}>
            Signature Story surfaces the one stat that defines this player's season. Check back after Week 4 when
            sample sizes clear the minimum volume gate for algorithmic selection.
          </p>
        </div>
      </div>
    );
  }

  // Loading state
  if (variant === 'loading') {
    return (
      <div
        className="border"
        style={{
          background: 'oklch(0.18 0.01 250)',
          borderColor: 'oklch(0.25 0.01 250)',
          borderRadius: 'var(--radius-lg)',
          containerType: 'inline-size',
          padding: 'var(--space-12)',
        }}
      >
        <div style={{ marginBottom: 'var(--space-8)' }}>
          <div
            style={{
              height: '0.75rem',
              width: '30%',
              background: 'oklch(0.25 0.01 250)',
              borderRadius: 'var(--radius-sm)',
              marginBottom: 'var(--space-2)',
            }}
          />
          <div
            style={{
              height: '2rem',
              width: '60%',
              background: 'oklch(0.25 0.01 250)',
              borderRadius: 'var(--radius-md)',
            }}
          />
        </div>
        <div className="signature-content-grid">
          <div>
            <div
              className="border"
              style={{
                background: 'oklch(0.20 0.01 250)',
                borderColor: 'oklch(0.28 0.01 250)',
                borderRadius: 'var(--radius-md)',
                height: '10rem',
                marginBottom: 'var(--space-6)',
              }}
            />
          </div>
          <div>
            <div
              style={{
                height: '0.75rem',
                width: '30%',
                background: 'oklch(0.25 0.01 250)',
                borderRadius: 'var(--radius-sm)',
                marginBottom: 'var(--space-3)',
              }}
            />
            <div
              style={{
                height: '4rem',
                width: '100%',
                background: 'oklch(0.22 0.01 250)',
                borderRadius: 'var(--radius-md)',
              }}
            />
          </div>
        </div>
        <style>
          {`
            .signature-content-grid {
              display: grid;
              grid-template-columns: 1fr;
              gap: var(--space-8);
            }

            @container (min-width: 720px) {
              .signature-content-grid {
                grid-template-columns: 1fr 1.6fr;
              }
            }
          `}
        </style>
      </div>
    );
  }

  // Error state
  if (variant === 'error') {
    return (
      <div
        className="border"
        style={{
          background: 'oklch(0.18 0.01 250)',
          borderColor: 'oklch(0.25 0.01 250)',
          borderRadius: 'var(--radius-lg)',
          containerType: 'inline-size',
          padding: 'var(--space-12)',
        }}
      >
        <div style={{ marginBottom: 'var(--space-8)' }}>
          <div
            className="font-medium tracking-wider uppercase"
            style={{
              color: 'oklch(0.6 0.02 250)',
              letterSpacing: '0.08em',
              fontSize: 'var(--fs-meta)',
              marginBottom: 'var(--space-2)',
            }}
          >
            SIGNATURE STORY
          </div>
          <h2
            className="leading-tight"
            style={{
              fontFamily: 'var(--font-display)',
              color: 'oklch(0.95 0.01 250)',
              fontWeight: 600,
              fontSize: 'var(--fs-h1)',
            }}
          >
            Load failed
          </h2>
        </div>
        <div
          className="border"
          style={{
            padding: 'var(--space-6)',
            background: 'oklch(0.20 0.01 250)',
            borderColor: 'oklch(0.28 0.01 250)',
            borderRadius: 'var(--radius-md)',
          }}
        >
          <p className="text-sm leading-relaxed" style={{ color: 'oklch(0.7 0.02 250)', marginBottom: 'var(--space-3)' }}>
            Could not retrieve signature metric data. Try refreshing the page.
          </p>
          <button
            type="button"
            className="text-sm font-semibold"
            style={{
              padding: 'var(--space-2) var(--space-4)',
              background: 'oklch(0.3 0.01 250)',
              color: 'oklch(0.95 0.01 250)',
              border: 'none',
              borderRadius: 'var(--radius-sm)',
              transition: 'background var(--motion-state)',
            }}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // Partial state: narrative missing
  const isPartial = variant === 'partial';
  const activeStory = isPartial
    ? {
        ...story,
        narrative: 'Narrative analysis pending — awaiting film breakdown from the analytics team.',
      }
    : story;

  return (
    <div
      className="border"
      style={{
        background: 'oklch(0.18 0.01 250)',
        borderColor: 'oklch(0.25 0.01 250)',
        borderRadius: 'var(--radius-lg)',
        containerType: 'inline-size',
        padding: 'var(--space-12)',
      }}
    >
      {/* Header */}
      <div style={{ marginBottom: 'var(--space-8)' }}>
        <div
          className="font-medium tracking-wider uppercase"
          style={{
            color: 'oklch(0.6 0.02 250)',
            letterSpacing: '0.08em',
            fontSize: 'var(--fs-meta)',
            marginBottom: 'var(--space-2)',
          }}
        >
          SIGNATURE STORY
        </div>
        <h2
          className="leading-tight"
          style={{
            fontFamily: 'var(--font-display)',
            color: 'oklch(0.95 0.01 250)',
            fontWeight: 600,
            fontSize: 'var(--fs-h1)',
          }}
        >
          {activeStory.headline}
        </h2>
      </div>

      {/* Main content grid */}
      <div className="signature-content-grid" style={{ marginBottom: 'var(--space-8)' }}>
        {/* Left: Hero stat + rank */}
        <div>
          <div
            className="border"
            style={{
              padding: 'var(--space-6)',
              background: 'oklch(0.20 0.01 250)',
              borderColor: 'oklch(0.28 0.01 250)',
              borderRadius: 'var(--radius-md)',
              boxShadow: 'var(--elevation-2)',
              marginBottom: 'var(--space-6)',
            }}
          >
            <div
              className="leading-none tabular-nums"
              style={{
                fontFamily: 'var(--font-display)',
                color: 'var(--percentile-100)',
                fontWeight: 700,
                fontSize: 'var(--fs-display)',
                marginBottom: 'var(--space-2)',
              }}
              aria-label={`${activeStory.stat.value} ${activeStory.stat.unit} ${activeStory.stat.context}`}
            >
              {activeStory.stat.value}
            </div>
            <div
              className="font-semibold"
              style={{
                color: 'oklch(0.95 0.01 250)',
                fontSize: 'var(--fs-body)',
                marginBottom: 'var(--space-1)',
              }}
            >
              {activeStory.stat.unit}
            </div>
            <div className="text-sm" style={{ color: 'oklch(0.6 0.02 250)' }}>
              {activeStory.stat.context}
            </div>
          </div>

          {/* Rank card */}
          <div
            className="border"
            style={{
              padding: 'var(--space-4)',
              background: 'oklch(0.20 0.01 250)',
              borderColor: 'oklch(0.28 0.01 250)',
              borderRadius: 'var(--radius-md)',
              display: 'flex',
              flexDirection: 'column',
              gap: 'var(--space-3)',
            }}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs" style={{ color: 'oklch(0.6 0.02 250)' }}>
                National rank
              </span>
              <span
                className="font-semibold tabular-nums"
                style={{
                  fontFamily: 'var(--font-display)',
                  color: 'var(--percentile-100)',
                  fontSize: 'var(--fs-h2)',
                }}
                aria-label={`Ranked number ${activeStory.rank.national} nationally`}
              >
                #{activeStory.rank.national}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs" style={{ color: 'oklch(0.6 0.02 250)' }}>
                Percentile vs P4
              </span>
              <span
                className="font-semibold tabular-nums"
                style={{
                  fontFamily: 'var(--font-display)',
                  color: 'var(--percentile-90)',
                  fontSize: 'var(--fs-h2)',
                }}
                aria-label={`${activeStory.rank.percentile}th percentile`}
              >
                {activeStory.rank.percentile}
                <span className="text-xs" style={{ fontSize: 'var(--fs-meta)' }}>
                  th
                </span>
              </span>
            </div>
          </div>
        </div>

        {/* Right: Narrative + chart */}
        <div>
          {/* Narrative */}
          <div style={{ marginBottom: 'var(--space-6)' }}>
            <div
              className="font-medium tracking-wider uppercase"
              style={{
                color: 'oklch(0.6 0.02 250)',
                letterSpacing: '0.08em',
                fontSize: 'var(--fs-meta)',
                marginBottom: 'var(--space-3)',
              }}
            >
              WHY IT MATTERS
            </div>
            <p
              className="leading-relaxed"
              style={{
                color: 'oklch(0.85 0.01 250)',
                fontSize: 'var(--fs-body)',
                lineHeight: 1.7,
              }}
            >
              {activeStory.narrative}
            </p>
          </div>

          {/* Weekly trend chart */}
          <div style={{ marginBottom: 'var(--space-6)' }}>
            <div
              className="font-medium tracking-wider uppercase"
              style={{
                color: 'oklch(0.6 0.02 250)',
                letterSpacing: '0.08em',
                fontSize: 'var(--fs-meta)',
                marginBottom: 'var(--space-3)',
              }}
            >
              11-WEEK TREND
            </div>
            <div className="relative">
              <svg width="100%" height="120" viewBox="0 0 500 120" className="w-full">
                <defs>
                  <linearGradient id="trendGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="var(--percentile-100)" stopOpacity="0.2" />
                    <stop offset="100%" stopColor="var(--percentile-100)" stopOpacity="0" />
                  </linearGradient>
                </defs>

                {/* Grid lines */}
                {[0.1, 0.2, 0.3, 0.4, 0.5].map((val) => (
                  <line
                    key={val}
                    x1="0"
                    y1={120 - (val / maxValue) * 100}
                    x2="500"
                    y2={120 - (val / maxValue) * 100}
                    stroke="oklch(0.25 0.01 250)"
                    strokeDasharray="4,4"
                    strokeWidth="1"
                  />
                ))}

                {/* P4 Average reference line */}
                <line
                  x1="0"
                  y1={120 - (0.12 / maxValue) * 100}
                  x2="500"
                  y2={120 - (0.12 / maxValue) * 100}
                  stroke="var(--percentile-50)"
                  strokeDasharray="2,2"
                  strokeWidth="1.5"
                />

                {/* Area fill */}
                <path
                  d={`M 0,120 ${activeStory.weeklyData
                    .map((d, i) => `L ${(i / (activeStory.weeklyData.length - 1)) * 500},${120 - (d.value / maxValue) * 100}`)
                    .join(' ')} L 500,120 Z`}
                  fill="url(#trendGradient)"
                />

                {/* Trend line */}
                <polyline
                  points={activeStory.weeklyData
                    .map((d, i) => `${(i / (activeStory.weeklyData.length - 1)) * 500},${120 - (d.value / maxValue) * 100}`)
                    .join(' ')}
                  fill="none"
                  stroke="var(--percentile-100)"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />

                {/* Data points */}
                {activeStory.weeklyData.map((d, i) => (
                  <circle
                    key={i}
                    cx={(i / (activeStory.weeklyData.length - 1)) * 500}
                    cy={120 - (d.value / maxValue) * 100}
                    r="3"
                    fill="var(--percentile-100)"
                  />
                ))}
              </svg>
              <div className="flex justify-between text-xs" style={{ marginTop: 'var(--space-2)', color: 'oklch(0.5 0.02 250)' }}>
                <span>Wk 1</span>
                <span style={{ color: 'var(--percentile-50)' }}>P4 Avg (0.12)</span>
                <span>Wk 11</span>
              </div>
            </div>
          </div>

          {/* Cohort comparison bars */}
          <div>
            <div
              className="font-medium tracking-wider uppercase"
              style={{
                color: 'oklch(0.6 0.02 250)',
                letterSpacing: '0.08em',
                fontSize: 'var(--fs-meta)',
                marginBottom: 'var(--space-3)',
              }}
            >
              VS COHORT
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
              {activeStory.cohortComparison.map((item) => (
                <div key={item.label}>
                  <div className="flex items-center justify-between text-xs" style={{ marginBottom: 'var(--space-1)' }}>
                    <span style={{ color: 'oklch(0.7 0.02 250)' }}>{item.label}</span>
                    <span className="font-semibold tabular-nums" style={{ color: 'oklch(0.95 0.01 250)' }}>
                      {item.value.toFixed(2)}
                    </span>
                  </div>
                  <div className="relative rounded-full" style={{ height: 'var(--space-2)', background: 'oklch(0.25 0.01 250)' }}>
                    <div
                      className="absolute inset-y-0 left-0 rounded-full"
                      style={{
                        width: `${(item.value / maxValue) * 100}%`,
                        background: item.color,
                        transition: 'width var(--motion-data-entry)',
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <style>
        {`
          .signature-content-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: var(--space-8);
          }

          @container (min-width: 720px) {
            .signature-content-grid {
              grid-template-columns: 1fr 1.6fr;
            }
          }
        `}
      </style>
    </div>
  );
}
