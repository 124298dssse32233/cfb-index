export default function PlayerStanding() {
  // 17 rungs across 6 tiers
  const rungs = [
    { id: 0, tier: 0, label: 'Walk-on', x: 0 },
    { id: 1, tier: 0, label: 'Scout team', x: 6.25 },
    { id: 2, tier: 1, label: 'Deep reserve', x: 12.5 },
    { id: 3, tier: 1, label: 'Backup', x: 18.75 },
    { id: 4, tier: 1, label: 'Rotational', x: 25 },
    { id: 5, tier: 2, label: 'Part-time starter', x: 31.25 },
    { id: 6, tier: 2, label: 'Starter', x: 37.5 },
    { id: 7, tier: 2, label: 'Impact starter', x: 43.75 },
    { id: 8, tier: 3, label: 'Watch-list', x: 50 },
    { id: 9, tier: 3, label: 'All-Conf HM', x: 56.25 },
    { id: 10, tier: 3, label: 'All-Conf 1st', x: 62.5 },
    { id: 11, tier: 3, label: 'National watch', x: 68.75 },
    { id: 12, tier: 4, label: 'All-American', x: 75 },
    { id: 13, tier: 4, label: 'Consensus AA', x: 81.25 },
    { id: 14, tier: 4, label: 'Unanimous AA', x: 87.5 },
    { id: 15, tier: 5, label: 'POTY Finalist', x: 93.75 },
    { id: 16, tier: 5, label: 'POTY Winner', x: 100 },
  ];

  const tiers = [
    { id: 0, label: 'On-team', rungs: [0, 1] },
    { id: 1, label: '2-deep', rungs: [2, 3, 4] },
    { id: 2, label: 'Starting', rungs: [5, 6, 7] }, // Changed from "Starter" to avoid collision with R6
    { id: 3, label: 'Recognized', rungs: [8, 9, 10, 11] },
    { id: 4, label: 'Elite', rungs: [12, 13, 14] },
    { id: 5, label: 'Apex', rungs: [15, 16] },
  ];

  const currentRung = 15; // CJ Carr at R15 (POTY Finalist)
  const lastSeasonRung = 2; // Ghost marker

  // NCAA-recognized (5) + Extended selectors (9)
  const ncaaSelectors = [
    { id: 'AP', name: 'AP', status: 'empty' },
    { id: 'AFCA', name: 'AFCA', status: 'empty' },
    { id: 'FWAA', name: 'FWAA', status: 'empty' },
    { id: 'WCFF', name: 'WCFF', status: 'gold' },
    { id: 'SN', name: 'SN', status: 'empty' },
  ];

  const extendedSelectors = [
    { id: 'SI', name: 'SI', status: 'silver' },
    { id: 'Athletic', name: 'Athletic', status: 'gold' },
    { id: 'USA', name: 'USA Today', status: 'empty' },
    { id: 'ESPN', name: 'ESPN', status: 'hm' },
    { id: 'CBS', name: 'CBS', status: 'empty' },
    { id: 'PFF', name: 'PFF', status: 'gold' },
    { id: 'CFN', name: 'CFN', status: 'empty' },
    { id: 'Athlon', name: 'Athlon', status: 'empty' },
    { id: 'Steele', name: 'Steele', status: 'silver' },
  ];

  return (
    <div
      className="standing-root border"
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
        <h2
          className="leading-none tracking-tight uppercase"
          style={{
            fontFamily: 'var(--font-display)',
            color: 'oklch(0.95 0.01 250)',
            fontWeight: 600,
            fontSize: 'var(--fs-h1)',
            marginBottom: 'var(--space-2)',
          }}
        >
          PLAYER STANDING
        </h2>
        <p className="text-sm" style={{ color: 'oklch(0.6 0.02 250)' }}>
          Current rung on the universal 17-step ladder. Accolade tabs nested below.
        </p>
      </div>

      {/* Current rung name (large, above rail) */}
      <div
        className="leading-none tracking-tight uppercase"
        style={{
          fontFamily: 'var(--font-display)',
          color: 'oklch(0.7 0.12 85)',
          fontWeight: 700,
          fontSize: 'var(--fs-display)',
          marginBottom: 'var(--space-6)',
        }}
        aria-label="Current player standing: Heisman Finalist, rung 15 of 17 on the ladder"
      >
        HEISMAN FINALIST
      </div>

      {/* The Rail - 17 ticks */}
      <div className="relative" style={{ marginBottom: 'var(--space-8)' }}>
        {/* Background rail */}
        <div
          className="rounded-full relative"
          style={{
            height: 'var(--space-2)',
            background: 'oklch(0.25 0.01 250)',
          }}
          role="meter"
          aria-label="Player standing rail showing progression from walk-on to Player of the Year winner"
          aria-valuenow={currentRung}
          aria-valuemin={0}
          aria-valuemax={16}
        >
          {/* Progress fill up to current rung */}
          <div
            className="absolute inset-y-0 left-0 rounded-full"
            style={{
              width: `${rungs[currentRung].x}%`,
              background: 'linear-gradient(90deg, oklch(0.3 0.01 250) 0%, oklch(0.7 0.12 85) 100%)',
              transition: 'width var(--motion-data-entry)',
            }}
          />

          {/* 17 tick marks - reduced density on narrow containers */}
          {rungs.map((rung, idx) => (
            <div
              key={rung.id}
              className="rail-tick absolute top-1/2 -translate-y-1/2 w-0.5 rounded-sm group"
              data-rung-id={rung.id}
              data-hide-mobile={idx % 2 !== 0 ? 'true' : 'false'}
              style={{
                left: `${rung.x}%`,
                height: 'var(--space-4)',
                background: rung.id <= currentRung ? 'oklch(0.4 0.01 250)' : 'oklch(0.3 0.01 250)',
              }}
              title={rung.label}
            >
              {/* Rung label on hover */}
              <div
                className="absolute left-1/2 -translate-x-1/2 whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none"
                style={{
                  top: 'var(--space-6)',
                  padding: 'var(--space-1) var(--space-2)',
                  background: 'oklch(0.22 0.01 250)',
                  color: 'oklch(0.8 0.02 250)',
                  fontSize: '11px',
                  transition: 'opacity var(--motion-reveal)',
                  borderRadius: 'var(--radius-sm)',
                }}
              >
                {rung.label}
              </div>
            </div>
          ))}

          {/* Ghost marker (last season) */}
          <div
            className="absolute top-1/2 -translate-y-1/2 rounded-full border-2 opacity-40"
            style={{
              left: `${rungs[lastSeasonRung].x}%`,
              width: 'var(--space-3)',
              height: 'var(--space-3)',
              borderColor: 'oklch(0.6 0.02 250)',
              background: 'transparent',
              transition: 'left var(--motion-data-entry)',
            }}
            aria-label={`Last season standing: ${rungs[lastSeasonRung].label}`}
          />

          {/* Current rung marker (gold) */}
          <div
            className="absolute top-1/2 -translate-y-1/2 rounded-full border-2"
            style={{
              left: `${rungs[currentRung].x}%`,
              width: '1.25rem',
              height: '1.25rem',
              background: 'oklch(0.7 0.12 85)',
              borderColor: 'oklch(0.8 0.1 90)',
              boxShadow: 'var(--elevation-2)',
              transition: 'left var(--motion-data-entry)',
            }}
            aria-label={`Current standing: ${rungs[currentRung].label}, rung ${currentRung} of 17`}
          />
        </div>

        {/* Tier labels below rail (default state) */}
        <div
          className="relative flex justify-between text-xs"
          style={{
            marginTop: 'var(--space-4)',
            color: 'oklch(0.5 0.02 250)',
          }}
        >
          {tiers.map((tier) => (
            <div key={tier.id} className="text-center" style={{ fontSize: '10px' }}>
              {tier.label}
            </div>
          ))}
        </div>
      </div>

      {/* Tier Pills */}
      <div className="flex flex-wrap" style={{ gap: 'var(--space-2)', marginBottom: 'var(--space-8)' }}>
        {tiers.map((tier) => (
          <button
            key={tier.id}
            className="text-xs font-semibold tracking-wider uppercase"
            style={{
              padding: 'var(--space-2) var(--space-4)',
              background: tier.id === 5 ? 'oklch(0.7 0.12 85)' : 'transparent',
              color: tier.id === 5 ? 'oklch(0.18 0.01 250)' : 'oklch(0.6 0.02 250)',
              border: tier.id === 5 ? 'none' : '1px solid oklch(0.3 0.01 250)',
              letterSpacing: '0.08em',
              borderRadius: '999px',
              transition:
                'background var(--motion-state), color var(--motion-state), border-color var(--motion-state)',
            }}
            aria-pressed={tier.id === 5}
            aria-label={`${tier.label} tier, contains rungs ${tier.rungs.join(', ')}`}
          >
            {tier.label}
          </button>
        ))}
      </div>

      {/* Rung Drawer (OPEN inline) */}
      <div
        className="border"
        style={{
          padding: 'var(--space-6)',
          marginBottom: 'var(--space-8)',
          background: 'oklch(0.20 0.01 250)',
          borderColor: 'oklch(0.28 0.01 250)',
          borderRadius: 'var(--radius-md)',
          boxShadow: 'var(--elevation-1)',
        }}
      >
        <div
          className="font-medium tracking-wider uppercase"
          style={{
            color: 'oklch(0.6 0.02 250)',
            letterSpacing: '0.08em',
            fontSize: 'var(--fs-meta)',
            marginBottom: 'var(--space-4)',
          }}
        >
          HEISMAN FINALIST · RUNG 15 OF 17
        </div>

        <div className="rung-drawer-grid" style={{ marginBottom: 'var(--space-6)' }}>
          {/* Why he's here */}
          <div>
            <div className="text-sm font-semibold" style={{ color: 'oklch(0.95 0.01 250)', marginBottom: 'var(--space-2)' }}>
              Why he's here
            </div>
            <div className="text-sm leading-relaxed" style={{ color: 'oklch(0.7 0.02 250)' }}>
              #15 Heisman nowcast. 2.2% win probability. 65.5% ballot probability. Elite EPA/dropback (90th pct vs P4).
            </div>
          </div>

          {/* What moves him up */}
          <div>
            <div className="text-sm font-semibold" style={{ color: 'oklch(0.95 0.01 250)', marginBottom: 'var(--space-2)' }}>
              What moves him up
            </div>
            <div className="text-sm leading-relaxed" style={{ color: 'oklch(0.7 0.02 250)' }}>
              Win the Heisman vote. Trophy ceremony invite already secured. Next rung is POTY Winner.
            </div>
          </div>

          {/* What moves him down */}
          <div>
            <div className="text-sm font-semibold" style={{ color: 'oklch(0.95 0.01 250)', marginBottom: 'var(--space-2)' }}>
              What moves him down
            </div>
            <div className="text-sm leading-relaxed" style={{ color: 'oklch(0.7 0.02 250)' }}>
              Falls below top-20 ballot standing. Drops from invited finalist tier. Returns to National watch.
            </div>
          </div>
        </div>

        {/* Trajectory sparkline WITH LABELS */}
        <div style={{ marginBottom: 'var(--space-6)' }}>
          <div
            className="font-medium"
            style={{
              color: 'oklch(0.6 0.02 250)',
              fontSize: 'var(--fs-meta)',
              marginBottom: 'var(--space-3)',
            }}
          >
            Weekly rung history
          </div>
          <div className="relative">
            <svg width="100%" height="80" viewBox="0 0 600 80" className="w-full">
              <defs>
                <linearGradient id="rungGradient" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor="oklch(0.4 0.01 250)" />
                  <stop offset="100%" stopColor="oklch(0.7 0.12 85)" />
                </linearGradient>
              </defs>
              {/* Rung threshold lines with labels */}
              <line x1="0" y1="25" x2="600" y2="25" stroke="oklch(0.35 0.01 250)" strokeDasharray="4,4" strokeWidth="1" />
              <text x="5" y="22" fill="oklch(0.5 0.02 250)" fontSize="9">
                Stay above for R15
              </text>
              <line x1="0" y1="45" x2="600" y2="45" stroke="oklch(0.35 0.01 250)" strokeDasharray="4,4" strokeWidth="1" />
              <text x="5" y="58" fill="oklch(0.5 0.02 250)" fontSize="9">
                Below drops to R12
              </text>
              {/* Trajectory line */}
              <polyline
                points="0,70 60,65 120,58 180,52 240,48 300,42 360,35 420,28 480,22 540,16 600,12"
                fill="none"
                stroke="url(#rungGradient)"
                strokeWidth="2.5"
              />
              <circle cx="600" cy="12" r="4" fill="oklch(0.7 0.12 85)" />
            </svg>
            {/* X-axis week labels */}
            <div className="flex justify-between text-xs" style={{ marginTop: 'var(--space-1)', color: 'oklch(0.5 0.02 250)' }}>
              <span style={{ fontSize: '10px' }}>Wk 1</span>
              <span style={{ fontSize: '10px' }}>Wk 4</span>
              <span style={{ fontSize: '10px' }}>Wk 8</span>
              <span style={{ fontSize: '10px' }}>Wk 11</span>
            </div>
          </div>
        </div>

        {/* Peer strip */}
        <div>
          <div
            className="font-medium"
            style={{
              color: 'oklch(0.6 0.02 250)',
              fontSize: 'var(--fs-meta)',
              marginBottom: 'var(--space-3)',
            }}
          >
            Also at POTY Finalist (Rung 15)
          </div>
          <div className="flex" style={{ gap: 'var(--space-3)' }}>
            {['Jalen Milroe', 'Quinn Ewers', 'Jaxson Dart', 'Drew Allar'].map((peer) => (
              <div
                key={peer}
                className="flex items-center text-xs"
                style={{
                  gap: 'var(--space-2)',
                  padding: 'var(--space-2) var(--space-3)',
                  background: 'oklch(0.22 0.01 250)',
                  color: 'oklch(0.8 0.02 250)',
                  borderRadius: 'var(--radius-sm)',
                  transition: 'background var(--motion-state)',
                }}
                aria-label={`${peer}, also at POTY Finalist standing`}
              >
                <div
                  className="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-semibold"
                  style={{ background: 'oklch(0.3 0.01 250)' }}
                  aria-hidden="true"
                >
                  {peer
                    .split(' ')
                    .map((n) => n[0])
                    .join('')}
                </div>
                <span>{peer.split(' ')[1]}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Accolade Tabs */}
      <div>
        <div
          className="font-medium tracking-wider uppercase"
          style={{
            color: 'oklch(0.6 0.02 250)',
            letterSpacing: '0.08em',
            fontSize: 'var(--fs-meta)',
            marginBottom: 'var(--space-4)',
          }}
        >
          ACCOLADE STREAMS
        </div>

        {/* Tab bar */}
        <div className="flex" style={{ gap: 'var(--space-2)', marginBottom: 'var(--space-6)' }}>
          {['Heisman', "Davey O'Brien", 'Manning', 'Unitas'].map((tab, idx) => (
            <button
              key={tab}
              className="text-sm font-semibold"
              style={{
                padding: 'var(--space-2) var(--space-4)',
                background: idx === 0 ? 'oklch(0.25 0.01 250)' : 'transparent',
                color: idx === 0 ? 'oklch(0.95 0.01 250)' : 'oklch(0.6 0.02 250)',
                border: idx === 0 ? 'none' : '1px solid oklch(0.28 0.01 250)',
                borderRadius: 'var(--radius-sm)',
                transition: 'background var(--motion-state), color var(--motion-state)',
              }}
              aria-pressed={idx === 0}
              aria-label={`${tab} award stream tab`}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Heisman tab content (expanded) */}
        <div
          className="border heisman-tab-content"
          style={{
            padding: 'var(--space-8)',
            background: 'oklch(0.20 0.01 250)',
            borderColor: 'oklch(0.28 0.01 250)',
            borderRadius: 'var(--radius-md)',
            boxShadow: 'var(--elevation-1)',
          }}
        >
          <div className="heisman-tab-grid" style={{ marginBottom: 'var(--space-8)' }}>
            {/* Left: Ladder */}
            <div>
              <div
                className="font-medium tracking-wider uppercase"
                style={{
                  color: 'oklch(0.6 0.02 250)',
                  letterSpacing: '0.08em',
                  fontSize: 'var(--fs-meta)',
                  marginBottom: 'var(--space-4)',
                }}
              >
                LADDER
              </div>
              <div className="flex flex-col" style={{ gap: 'var(--space-3)' }}>
                {['Watch', 'Conf', 'AA', 'POTY'].map((step, idx) => (
                  <div
                    key={step}
                    className="flex items-center"
                    style={{
                      gap: 'var(--space-3)',
                      opacity: idx === 3 ? 1 : 0.5,
                      transition: 'opacity var(--motion-state)',
                    }}
                  >
                    <div
                      className="rounded-full flex items-center justify-center text-xs font-semibold"
                      style={{
                        width: '2rem',
                        height: '2rem',
                        background: idx === 3 ? 'oklch(0.7 0.12 85)' : 'oklch(0.25 0.01 250)',
                        color: idx === 3 ? 'oklch(0.18 0.01 250)' : 'oklch(0.6 0.02 250)',
                      }}
                      aria-label={`Heisman ladder step ${idx + 1}: ${step}${idx === 3 ? ', current' : ''}`}
                    >
                      {idx + 1}
                    </div>
                    <span
                      className="text-sm font-medium"
                      style={{ color: idx === 3 ? 'oklch(0.95 0.01 250)' : 'oklch(0.6 0.02 250)' }}
                    >
                      {step}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Middle: 3 probability tiles */}
            <div>
              <div
                className="font-medium tracking-wider uppercase"
                style={{
                  color: 'oklch(0.6 0.02 250)',
                  letterSpacing: '0.08em',
                  fontSize: 'var(--fs-meta)',
                  marginBottom: 'var(--space-4)',
                }}
              >
                PROBABILITIES
              </div>
              <div className="probability-tiles-grid">
                {[
                  { label: 'Win', value: '2.2%', color: 'oklch(0.7 0.12 85)' },
                  { label: 'Finalist', value: '0.0%', color: 'oklch(0.6 0.02 250)' },
                  { label: 'Ballot', value: '65.5%', color: 'var(--percentile-75)' },
                ].map((tile) => (
                  <div
                    key={tile.label}
                    className="border"
                    style={{
                      padding: 'var(--space-4)',
                      background: 'oklch(0.22 0.01 250)',
                      borderColor: 'oklch(0.3 0.01 250)',
                      borderRadius: 'var(--radius-sm)',
                      transition: 'transform var(--motion-state)',
                    }}
                  >
                    <div
                      style={{
                        color: 'oklch(0.6 0.02 250)',
                        fontSize: 'var(--fs-meta)',
                        marginBottom: 'var(--space-2)',
                      }}
                    >
                      {tile.label}
                    </div>
                    <div
                      className="leading-none tabular-nums"
                      style={{
                        fontFamily: 'var(--font-display)',
                        color: tile.color,
                        fontWeight: 700,
                        fontSize: 'var(--fs-h2)',
                      }}
                      aria-label={`Heisman ${tile.label} probability: ${tile.value}`}
                    >
                      {tile.value}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Right: What needs to happen */}
            <div>
              <div
                className="font-medium tracking-wider uppercase"
                style={{
                  color: 'oklch(0.6 0.02 250)',
                  letterSpacing: '0.08em',
                  fontSize: 'var(--fs-meta)',
                  marginBottom: 'var(--space-4)',
                }}
              >
                WHAT NEEDS TO HAPPEN
              </div>
              <div className="text-sm leading-relaxed" style={{ color: 'oklch(0.7 0.02 250)' }}>
                <p style={{ marginBottom: 'var(--space-3)' }}>
                  Already at finalist tier. To win: needs Cam Ward to stumble in playoff + dominant CFP semifinal
                  performance.
                </p>
                <p>
                  Downside scenario: loss to Georgia in CFP drops him below Ashton Jeanty and Dylan Raiola in final
                  ballots.
                </p>
              </div>
            </div>
          </div>

          {/* Selector Grid - NCAA-RECOGNIZED GROUPING */}
          <div>
            <div
              className="font-medium tracking-wider uppercase"
              style={{
                color: 'oklch(0.6 0.02 250)',
                letterSpacing: '0.08em',
                fontSize: 'var(--fs-meta)',
                marginBottom: 'var(--space-4)',
              }}
            >
              ALL-AMERICA SELECTOR GRID
            </div>

            {/* NCAA-recognized selectors (primary row) */}
            <div
              style={{
                color: 'oklch(0.5 0.02 250)',
                fontSize: '10px',
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
                marginBottom: 'var(--space-2)',
                paddingBottom: 'var(--space-1)',
              }}
            >
              NCAA-Recognized (Consensus Makers)
            </div>
            <div className="ncaa-selector-grid" style={{ marginBottom: 'var(--space-6)' }}>
              {ncaaSelectors.map((selector) => {
                let bgColor = 'oklch(0.25 0.01 250)';
                let textColor = 'oklch(0.5 0.02 250)';
                let borderColor = 'oklch(0.3 0.01 250)';

                if (selector.status === 'gold') {
                  bgColor = 'oklch(0.7 0.12 85)';
                  textColor = 'oklch(0.18 0.01 250)';
                  borderColor = 'oklch(0.8 0.1 90)';
                } else if (selector.status === 'silver') {
                  bgColor = 'oklch(0.55 0.02 250)';
                  textColor = 'oklch(0.18 0.01 250)';
                  borderColor = 'oklch(0.65 0.02 250)';
                } else if (selector.status === 'hm') {
                  bgColor = 'oklch(0.35 0.01 250)';
                  textColor = 'oklch(0.7 0.02 250)';
                  borderColor = 'oklch(0.4 0.01 250)';
                }

                const statusLabel =
                  selector.status === 'gold'
                    ? 'first team'
                    : selector.status === 'silver'
                      ? 'second team'
                      : selector.status === 'hm'
                        ? 'honorable mention'
                        : 'not yet selected';

                return (
                  <div
                    key={selector.id}
                    className="border text-center flex items-center justify-center"
                    style={{
                      padding: 'var(--space-3)',
                      minHeight: '3.5rem',
                      background: bgColor,
                      borderColor: borderColor,
                      borderRadius: 'var(--radius-sm)',
                      transition: 'transform var(--motion-state)',
                      boxShadow: selector.status === 'gold' ? 'var(--elevation-1)' : 'none',
                    }}
                    aria-label={`${selector.name}, NCAA-recognized selector, ${statusLabel}`}
                  >
                    <span className="text-xs font-semibold" style={{ color: textColor }}>
                      {selector.name}
                    </span>
                  </div>
                );
              })}
            </div>

            {/* Extended selectors (secondary row) */}
            <div
              style={{
                color: 'oklch(0.5 0.02 250)',
                fontSize: '10px',
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
                marginBottom: 'var(--space-2)',
                paddingBottom: 'var(--space-1)',
              }}
            >
              Extended Selectors
            </div>
            <div className="extended-selector-grid" style={{ marginBottom: 'var(--space-4)' }}>
              {extendedSelectors.map((selector) => {
                let bgColor = 'oklch(0.25 0.01 250)';
                let textColor = 'oklch(0.5 0.02 250)';
                let borderColor = 'oklch(0.3 0.01 250)';

                if (selector.status === 'gold') {
                  bgColor = 'oklch(0.7 0.12 85)';
                  textColor = 'oklch(0.18 0.01 250)';
                  borderColor = 'oklch(0.8 0.1 90)';
                } else if (selector.status === 'silver') {
                  bgColor = 'oklch(0.55 0.02 250)';
                  textColor = 'oklch(0.18 0.01 250)';
                  borderColor = 'oklch(0.65 0.02 250)';
                } else if (selector.status === 'hm') {
                  bgColor = 'oklch(0.35 0.01 250)';
                  textColor = 'oklch(0.7 0.02 250)';
                  borderColor = 'oklch(0.4 0.01 250)';
                }

                const statusLabel =
                  selector.status === 'gold'
                    ? 'first team'
                    : selector.status === 'silver'
                      ? 'second team'
                      : selector.status === 'hm'
                        ? 'honorable mention'
                        : 'not yet selected';

                return (
                  <div
                    key={selector.id}
                    className="border text-center flex items-center justify-center"
                    style={{
                      padding: 'var(--space-2)',
                      minHeight: '3rem',
                      background: bgColor,
                      borderColor: borderColor,
                      borderRadius: 'var(--radius-sm)',
                      transition: 'transform var(--motion-state)',
                      boxShadow: selector.status === 'gold' ? 'var(--elevation-1)' : 'none',
                    }}
                    aria-label={`${selector.name}, extended selector, ${statusLabel}`}
                  >
                    <span className="text-xs font-semibold" style={{ color: textColor }}>
                      {selector.name}
                    </span>
                  </div>
                );
              })}
            </div>

            {/* Legend */}
            <div
              className="flex"
              style={{
                gap: 'var(--space-6)',
                color: 'oklch(0.6 0.02 250)',
                fontSize: 'var(--fs-meta)',
              }}
            >
              <div className="flex items-center" style={{ gap: 'var(--space-2)' }}>
                <div
                  className="border"
                  style={{
                    width: 'var(--space-4)',
                    height: 'var(--space-4)',
                    background: 'oklch(0.7 0.12 85)',
                    borderColor: 'oklch(0.8 0.1 90)',
                    borderRadius: 'var(--radius-sm)',
                  }}
                  aria-hidden="true"
                />
                <span>1st team</span>
              </div>
              <div className="flex items-center" style={{ gap: 'var(--space-2)' }}>
                <div
                  className="border"
                  style={{
                    width: 'var(--space-4)',
                    height: 'var(--space-4)',
                    background: 'oklch(0.55 0.02 250)',
                    borderColor: 'oklch(0.65 0.02 250)',
                    borderRadius: 'var(--radius-sm)',
                  }}
                  aria-hidden="true"
                />
                <span>2nd team</span>
              </div>
              <div className="flex items-center" style={{ gap: 'var(--space-2)' }}>
                <div
                  className="border"
                  style={{
                    width: 'var(--space-4)',
                    height: 'var(--space-4)',
                    background: 'oklch(0.35 0.01 250)',
                    borderColor: 'oklch(0.4 0.01 250)',
                    borderRadius: 'var(--radius-sm)',
                  }}
                  aria-hidden="true"
                />
                <span>HM</span>
              </div>
              <div className="flex items-center" style={{ gap: 'var(--space-2)' }}>
                <div
                  className="border"
                  style={{
                    width: 'var(--space-4)',
                    height: 'var(--space-4)',
                    background: 'oklch(0.25 0.01 250)',
                    borderColor: 'oklch(0.3 0.01 250)',
                    borderRadius: 'var(--radius-sm)',
                  }}
                  aria-hidden="true"
                />
                <span>Not yet</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <style>
        {`
          /* Container query breakpoints for responsive grids */
          .rung-drawer-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: var(--space-6);
          }

          @container (min-width: 720px) {
            .rung-drawer-grid {
              grid-template-columns: repeat(3, 1fr);
            }
          }

          .heisman-tab-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: var(--space-8);
          }

          @container (min-width: 900px) {
            .heisman-tab-grid {
              grid-template-columns: 200px 1fr 300px;
            }
          }

          .probability-tiles-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: var(--space-4);
          }

          @container (min-width: 500px) {
            .probability-tiles-grid {
              grid-template-columns: repeat(3, 1fr);
            }
          }

          .ncaa-selector-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: var(--space-3);
          }

          @container (min-width: 500px) {
            .ncaa-selector-grid {
              grid-template-columns: repeat(5, 1fr);
            }
          }

          .extended-selector-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: var(--space-3);
          }

          @container (min-width: 800px) {
            .extended-selector-grid {
              grid-template-columns: repeat(9, 1fr);
            }
          }

          /* Reduced tick density on narrow containers */
          @container (max-width: 600px) {
            .rail-tick[data-hide-mobile="true"] {
              display: none;
            }

            .standing-root {
              padding: var(--space-6) !important;
            }
          }
        `}
      </style>
    </div>
  );
}
