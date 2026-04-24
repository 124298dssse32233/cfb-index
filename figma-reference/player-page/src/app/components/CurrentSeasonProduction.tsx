// Current Season Production — 30s tier
// Traditional box score with rank + percentile context on every number

import { useState } from 'react';

type StateVariant = 'full' | 'empty' | 'loading' | 'partial' | 'error';

interface StatRow {
  label: string;
  value: string | number;
  rank?: number;
  percentile?: number;
}

interface SeasonStats {
  passing: StatRow[];
  rushing: StatRow[];
  misc: StatRow[];
}

export default function CurrentSeasonProduction({ variant = 'full' }: { variant?: StateVariant }) {
  const [isOpponentAdjusted, setIsOpponentAdjusted] = useState(true);

  const stats: SeasonStats = {
    passing: [
      { label: 'Completions', value: 287, rank: 8, percentile: 88 },
      { label: 'Attempts', value: 412, rank: 12, percentile: 82 },
      { label: 'Completion %', value: '69.7%', rank: 18, percentile: 76 },
      { label: 'Yards', value: 4203, rank: 5, percentile: 92 },
      { label: 'Touchdowns', value: 38, rank: 3, percentile: 95 },
      { label: 'Interceptions', value: 6, rank: 4, percentile: 94 },
      { label: 'Passer rating', value: 168.4, rank: 9, percentile: 87 },
    ],
    rushing: [
      { label: 'Attempts', value: 52, rank: 38, percentile: 42 },
      { label: 'Yards', value: 218, rank: 29, percentile: 54 },
      { label: 'Yards/attempt', value: 4.2, rank: 22, percentile: 68 },
      { label: 'Touchdowns', value: 4, rank: 18, percentile: 72 },
    ],
    misc: [
      { label: 'Sacks', value: 14, rank: 8, percentile: 88 },
      { label: 'Fumbles lost', value: 2, rank: 12, percentile: 82 },
      { label: 'Total TDs', value: 42, rank: 4, percentile: 94 },
    ],
  };

  const partialStats: SeasonStats = {
    passing: [
      { label: 'Completions', value: 287, rank: 8, percentile: 88 },
      { label: 'Attempts', value: 412, rank: 12, percentile: 82 },
      { label: 'Completion %', value: '69.7%', rank: 18, percentile: 76 },
      { label: 'Yards', value: 4203, rank: 5, percentile: 92 },
      { label: 'Touchdowns', value: 38, rank: 3, percentile: 95 },
      { label: 'Interceptions', value: 6, rank: 4, percentile: 94 },
      { label: 'Passer rating', value: '—', percentile: undefined },
    ],
    rushing: [
      { label: 'Attempts', value: 52 },
      { label: 'Yards', value: 218 },
      { label: 'Yards/attempt', value: 4.2 },
      { label: 'Touchdowns', value: 4 },
    ],
    misc: [
      { label: 'Sacks', value: 14, rank: 8, percentile: 88 },
      { label: 'Fumbles lost', value: 2, rank: 12, percentile: 82 },
      { label: 'Total TDs', value: 42, rank: 4, percentile: 94 },
    ],
  };

  function StatCard({ title, rows }: { title: string; rows: StatRow[] }) {
    return (
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
          {title}
        </div>
        <div
          className="border"
          style={{
            background: 'oklch(0.20 0.01 250)',
            borderColor: 'oklch(0.28 0.01 250)',
            borderRadius: 'var(--radius-md)',
            padding: 'var(--space-4)',
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--space-3)',
          }}
        >
          {rows.map((row, idx) => (
            <div key={idx} className="flex items-center justify-between" style={{ gap: 'var(--space-4)' }}>
              <span className="text-sm" style={{ color: 'oklch(0.7 0.02 250)', flex: '1 1 auto' }}>
                {row.label}
              </span>
              <div className="flex items-center" style={{ gap: 'var(--space-3)', flex: '0 0 auto' }}>
                <span
                  className="font-semibold tabular-nums"
                  style={{
                    color: 'oklch(0.95 0.01 250)',
                    fontSize: 'var(--fs-body)',
                    minWidth: '3.5rem',
                    textAlign: 'right',
                  }}
                >
                  {row.value}
                </span>
                {row.percentile !== undefined && (
                  <div
                    className="text-xs font-semibold tabular-nums"
                    style={{
                      padding: 'var(--space-1) var(--space-2)',
                      background:
                        row.percentile >= 90
                          ? 'var(--percentile-100)'
                          : row.percentile >= 75
                            ? 'var(--percentile-90)'
                            : row.percentile >= 50
                              ? 'var(--percentile-75)'
                              : 'var(--percentile-25)',
                      color: 'oklch(0.18 0.01 250)',
                      borderRadius: '999px',
                      minWidth: '2.5rem',
                      textAlign: 'center',
                    }}
                    aria-label={`${row.percentile}th percentile`}
                  >
                    {row.percentile}
                    <span style={{ fontSize: '9px' }}>th</span>
                  </div>
                )}
                {row.percentile === undefined && row.rank === undefined && (
                  <div style={{ minWidth: '2.5rem' }} />
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

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
            CURRENT SEASON PRODUCTION
          </h2>
          <p className="text-sm" style={{ color: 'oklch(0.6 0.02 250)' }}>
            Stats unavailable · Season has not begun
          </p>
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
            Production metrics will populate after Week 1. Check back after the first snap for passing, rushing, and
            turnover data.
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
              height: '2rem',
              width: '60%',
              background: 'oklch(0.25 0.01 250)',
              borderRadius: 'var(--radius-md)',
              marginBottom: 'var(--space-2)',
            }}
          />
          <div
            style={{
              height: '1rem',
              width: '40%',
              background: 'oklch(0.22 0.01 250)',
              borderRadius: 'var(--radius-sm)',
            }}
          />
        </div>
        <div className="production-grid">
          {[1, 2, 3].map((idx) => (
            <div key={idx}>
              <div
                style={{
                  height: '0.75rem',
                  width: '40%',
                  background: 'oklch(0.25 0.01 250)',
                  borderRadius: 'var(--radius-sm)',
                  marginBottom: 'var(--space-3)',
                }}
              />
              <div
                className="border"
                style={{
                  background: 'oklch(0.20 0.01 250)',
                  borderColor: 'oklch(0.28 0.01 250)',
                  borderRadius: 'var(--radius-md)',
                  padding: 'var(--space-4)',
                  height: '12rem',
                }}
              />
            </div>
          ))}
        </div>
        <style>
          {`
            .production-grid {
              display: grid;
              grid-template-columns: 1fr;
              gap: var(--space-6);
            }

            @container (min-width: 900px) {
              .production-grid {
                grid-template-columns: repeat(3, 1fr);
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
            CURRENT SEASON PRODUCTION
          </h2>
          <p className="text-sm" style={{ color: 'oklch(0.6 0.02 250)' }}>
            Stats unavailable · Data sync failed
          </p>
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
            Could not load season statistics. Check your connection and try again.
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

  // Full or partial state
  const activeStats = variant === 'partial' ? partialStats : stats;

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
          CURRENT SEASON PRODUCTION
        </h2>
        <p className="text-sm" style={{ color: 'oklch(0.6 0.02 250)' }}>
          {variant === 'partial'
            ? 'Box score · Opponent-adjusted · Partial data (rushing ranks pending)'
            : 'Box score · Rank + percentile context · Opponent-adjusted'}
        </p>
      </div>

      {/* Toggle chip */}
      <div style={{ marginBottom: 'var(--space-6)' }}>
        <div className="flex flex-wrap" style={{ gap: 'var(--space-2)' }}>
          <button
            type="button"
            className="text-xs font-semibold tracking-wider uppercase"
            style={{
              padding: 'var(--space-3) var(--space-5)',
              background: isOpponentAdjusted ? 'oklch(0.3 0.01 250)' : 'transparent',
              color: isOpponentAdjusted ? 'oklch(0.95 0.01 250)' : 'oklch(0.6 0.02 250)',
              border: isOpponentAdjusted ? 'none' : '1px solid oklch(0.28 0.01 250)',
              letterSpacing: '0.08em',
              borderRadius: '999px',
              transition: 'background var(--motion-state), color var(--motion-state)',
              minHeight: '44px',
            }}
            onClick={() => setIsOpponentAdjusted(true)}
            aria-pressed={isOpponentAdjusted}
          >
            Opponent-adjusted
          </button>
          <button
            type="button"
            className="text-xs font-semibold tracking-wider uppercase"
            style={{
              padding: 'var(--space-3) var(--space-5)',
              background: !isOpponentAdjusted ? 'oklch(0.3 0.01 250)' : 'transparent',
              color: !isOpponentAdjusted ? 'oklch(0.95 0.01 250)' : 'oklch(0.6 0.02 250)',
              border: !isOpponentAdjusted ? 'none' : '1px solid oklch(0.28 0.01 250)',
              letterSpacing: '0.08em',
              borderRadius: '999px',
              transition: 'background var(--motion-state), color var(--motion-state)',
              minHeight: '44px',
            }}
            onClick={() => setIsOpponentAdjusted(false)}
            aria-pressed={!isOpponentAdjusted}
          >
            Raw
          </button>
        </div>
      </div>

      {/* Stats grid */}
      <div className="production-grid">
        <StatCard title="PASSING" rows={activeStats.passing} />
        <StatCard title="RUSHING" rows={activeStats.rushing} />
        <StatCard title="MISC" rows={activeStats.misc} />
      </div>

      <style>
        {`
          .production-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: var(--space-6);
          }

          @container (min-width: 900px) {
            .production-grid {
              grid-template-columns: repeat(3, 1fr);
            }
          }
        `}
      </style>
    </div>
  );
}
