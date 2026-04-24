// Standing Variants Board — 5 rung extremes to test module dignity at all tiers

interface StandingVariantProps {
  currentRung: number;
  playerName: string;
  position: string;
  team: string;
  stats?: {
    why: string;
    movesUp: string;
    movesDown: string;
  };
}

function StandingVariant({ currentRung, playerName, position, team, stats }: StandingVariantProps) {
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
    { id: 0, label: 'On-team' },
    { id: 1, label: '2-deep' },
    { id: 2, label: 'Starting' },
    { id: 3, label: 'Recognized' },
    { id: 4, label: 'Elite' },
    { id: 5, label: 'Apex' },
  ];

  const currentTier = rungs[currentRung].tier;
  const rungName = rungs[currentRung].label.toUpperCase();

  return (
    <div
      className="border"
      style={{
        background: 'oklch(0.18 0.01 250)',
        borderColor: 'oklch(0.25 0.01 250)',
        borderRadius: 'var(--radius-lg)',
        padding: 'var(--space-8)',
        containerType: 'inline-size',
      }}
    >
      {/* Variant header */}
      <div style={{ marginBottom: 'var(--space-6)' }}>
        <div
          className="font-medium tracking-wider uppercase"
          style={{
            color: 'oklch(0.6 0.02 250)',
            letterSpacing: '0.08em',
            fontSize: 'var(--fs-meta)',
            marginBottom: 'var(--space-2)',
          }}
        >
          {position} · {team}
        </div>
        <h3
          className="font-semibold"
          style={{
            fontFamily: 'var(--font-display)',
            color: 'oklch(0.95 0.01 250)',
            fontSize: 'var(--fs-h2)',
            marginBottom: 'var(--space-1)',
          }}
        >
          {playerName}
        </h3>
      </div>

      {/* Current rung name */}
      <div
        className="leading-none tracking-tight uppercase"
        style={{
          fontFamily: 'var(--font-display)',
          color: currentRung >= 12 ? 'oklch(0.7 0.12 85)' : 'oklch(0.7 0.02 250)',
          fontWeight: 700,
          fontSize: 'var(--fs-h2)',
          marginBottom: 'var(--space-4)',
        }}
      >
        {rungName}
      </div>

      {/* The Rail */}
      <div className="relative" style={{ marginBottom: 'var(--space-6)' }}>
        <div
          className="rounded-full relative"
          style={{
            height: 'var(--space-2)',
            background: 'oklch(0.25 0.01 250)',
          }}
        >
          {/* Progress fill */}
          <div
            className="absolute inset-y-0 left-0 rounded-full"
            style={{
              width: `${rungs[currentRung].x}%`,
              background:
                currentRung >= 12
                  ? 'linear-gradient(90deg, oklch(0.3 0.01 250) 0%, oklch(0.7 0.12 85) 100%)'
                  : 'oklch(0.35 0.01 250)',
              transition: 'width var(--motion-data-entry)',
            }}
          />

          {/* 17 tick marks - every other for density */}
          {rungs
            .filter((_, idx) => idx % 2 === 0)
            .map((rung) => (
              <div
                key={rung.id}
                className="absolute top-1/2 -translate-y-1/2 w-0.5 rounded-sm"
                style={{
                  left: `${rung.x}%`,
                  height: 'var(--space-3)',
                  background: rung.id <= currentRung ? 'oklch(0.4 0.01 250)' : 'oklch(0.3 0.01 250)',
                }}
              />
            ))}

          {/* Current rung marker */}
          <div
            className="absolute top-1/2 -translate-y-1/2 rounded-full border-2"
            style={{
              left: `${rungs[currentRung].x}%`,
              width: '1rem',
              height: '1rem',
              background: currentRung >= 12 ? 'oklch(0.7 0.12 85)' : 'oklch(0.6 0.02 250)',
              borderColor: currentRung >= 12 ? 'oklch(0.8 0.1 90)' : 'oklch(0.7 0.02 250)',
              boxShadow: currentRung >= 12 ? 'var(--elevation-2)' : 'var(--elevation-1)',
              transition: 'left var(--motion-data-entry)',
            }}
          />
        </div>
      </div>

      {/* Tier Pills */}
      <div className="flex flex-wrap" style={{ gap: 'var(--space-2)', marginBottom: 'var(--space-6)' }}>
        {tiers.map((tier) => (
          <div
            key={tier.id}
            className="text-xs font-semibold tracking-wider uppercase"
            style={{
              padding: 'var(--space-1) var(--space-3)',
              background: tier.id === currentTier ? 'oklch(0.3 0.01 250)' : 'transparent',
              color: tier.id === currentTier ? 'oklch(0.95 0.01 250)' : 'oklch(0.5 0.02 250)',
              border: tier.id === currentTier ? 'none' : '1px solid oklch(0.28 0.01 250)',
              letterSpacing: '0.08em',
              borderRadius: '999px',
              fontSize: '10px',
            }}
          >
            {tier.label}
          </div>
        ))}
      </div>

      {/* Rung summary */}
      {stats ? (
        <div
          className="border"
          style={{
            padding: 'var(--space-4)',
            background: 'oklch(0.20 0.01 250)',
            borderColor: 'oklch(0.28 0.01 250)',
            borderRadius: 'var(--radius-md)',
            boxShadow: 'var(--elevation-1)',
          }}
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
            <div>
              <div
                className="text-xs font-semibold"
                style={{ color: 'oklch(0.95 0.01 250)', marginBottom: 'var(--space-1)' }}
              >
                Why here
              </div>
              <div className="text-xs leading-relaxed" style={{ color: 'oklch(0.7 0.02 250)' }}>
                {stats.why}
              </div>
            </div>
            <div>
              <div
                className="text-xs font-semibold"
                style={{ color: 'oklch(0.95 0.01 250)', marginBottom: 'var(--space-1)' }}
              >
                Next step
              </div>
              <div className="text-xs leading-relaxed" style={{ color: 'oklch(0.7 0.02 250)' }}>
                {stats.movesUp}
              </div>
            </div>
          </div>
        </div>
      ) : (
        // Shape-accurate skeleton for empty data
        <div
          className="border"
          style={{
            padding: 'var(--space-4)',
            background: 'oklch(0.20 0.01 250)',
            borderColor: 'oklch(0.28 0.01 250)',
            borderRadius: 'var(--radius-md)',
          }}
        >
          <div className="text-xs leading-relaxed" style={{ color: 'oklch(0.6 0.02 250)' }}>
            Rung placement based on roster status. Production metrics will populate when snaps accumulate.
          </div>
        </div>
      )}
    </div>
  );
}

export default function StandingVariants() {
  const variants = [
    {
      currentRung: 0,
      playerName: 'Marcus Chen',
      position: 'QB',
      team: 'Vanderbilt',
      stats: undefined, // No stats for walk-on - honest empty state
    },
    {
      currentRung: 3,
      playerName: 'Tyler Brooks',
      position: 'QB',
      team: 'Kentucky',
      stats: {
        why: 'QB2 on depth chart. 8 snaps in garbage time vs Tennessee. Completed 2/5 passes.',
        movesUp: 'Injury to starter or earn rotational role in blowouts. Need 15%+ snap share for R04.',
        movesDown: 'Drops to scout team if passed on depth chart by incoming freshman.',
      },
    },
    {
      currentRung: 6,
      playerName: 'Jake Morrison',
      position: 'QB',
      team: 'Iowa State',
      stats: {
        why: 'Started 9 of 11 games. 62% snap share. 58% completion rate (48th pct vs P4 QBs).',
        movesUp: "Crack 70th percentile in EPA/dropback or land on Davey O'Brien watch list.",
        movesDown: 'Benched mid-season or snap share falls below 60%. Returns to R05.',
      },
    },
    {
      currentRung: 12,
      playerName: 'Dylan Hayes',
      position: 'QB',
      team: 'Penn State',
      stats: {
        why: 'Named to FWAA All-America 1st team. 88th percentile CPOE. 4,200 passing yards.',
        movesUp: 'Earn 3+ NCAA-recognized All-America selections for Consensus (R13).',
        movesDown: 'Drops to R11 if end-of-season voting excludes from final ballots.',
      },
    },
    {
      currentRung: 15,
      playerName: 'CJ Carr',
      position: 'QB',
      team: 'Notre Dame',
      stats: {
        why: '#15 Heisman nowcast. 2.2% win probability. Elite EPA/dropback (90th pct vs P4).',
        movesUp: 'Win the Heisman vote. Trophy ceremony invite already secured.',
        movesDown: 'Falls below top-20 ballot standing. Returns to R11 (National watch).',
      },
    },
  ];

  return (
    <div style={{ containerType: 'inline-size' }}>
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
          STANDING VARIANTS BOARD
        </h2>
        <p className="text-sm" style={{ color: 'oklch(0.6 0.02 250)' }}>
          5 rung extremes — walk-on to Heisman finalist. Module dignity test at all tiers.
        </p>
      </div>

      <div className="standing-variants-grid">
        {variants.map((variant, idx) => (
          <StandingVariant key={idx} {...variant} />
        ))}
      </div>

      <style>
        {`
          .standing-variants-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: var(--space-6);
          }

          @container (min-width: 900px) {
            .standing-variants-grid {
              grid-template-columns: repeat(2, 1fr);
            }
          }

          @container (min-width: 1200px) {
            .standing-variants-grid {
              grid-template-columns: repeat(3, 1fr);
            }
          }
        `}
      </style>
    </div>
  );
}
