// Splits — 30s headline row / 5m deep tabs
// Progressive disclosure: 4 headline split pairs visible by default, deep tabs behind Drawer primitive

import { useState } from 'react';

type StateVariant = 'full' | 'empty' | 'loading' | 'partial' | 'error';
type DeepTabId = 'situational' | 'down-distance' | 'personnel' | 'opponent-tier';

interface SplitPair {
  label: string;
  leftLabel: string;
  leftValue: number;
  leftPercentile: number;
  rightLabel: string;
  rightValue: number;
  rightPercentile: number;
}

interface DeepSplit {
  situation: string;
  completions: number;
  attempts: number;
  yards: number;
  tds: number;
  ints: number;
  rating: number;
  percentile: number;
}

export default function Splits({ variant = 'full' }: { variant?: StateVariant }) {
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<DeepTabId>('situational');

  const headlineSplits: SplitPair[] = [
    {
      label: 'Home vs Away',
      leftLabel: 'Home',
      leftValue: 171.2,
      leftPercentile: 89,
      rightLabel: 'Away',
      rightValue: 165.8,
      rightPercentile: 85,
    },
    {
      label: 'vs P4 vs vs G5',
      leftLabel: 'vs P4',
      leftValue: 168.4,
      leftPercentile: 87,
      rightLabel: 'vs G5',
      rightValue: 178.6,
      rightPercentile: 93,
    },
    {
      label: '1st half vs 2nd half',
      leftLabel: '1st half',
      leftValue: 164.2,
      leftPercentile: 83,
      rightLabel: '2nd half',
      rightValue: 172.8,
      rightPercentile: 90,
    },
    {
      label: 'Red zone',
      leftLabel: 'Red zone',
      leftValue: 182.4,
      leftPercentile: 95,
      rightLabel: 'Outside RZ',
      rightValue: 166.1,
      rightPercentile: 86,
    },
  ];

  const deepSplitsData: Record<DeepTabId, DeepSplit[]> = {
    situational: [
      { situation: 'Under pressure', completions: 42, attempts: 68, yards: 512, tds: 6, ints: 1, rating: 156.2, percentile: 92 },
      { situation: 'Clean pocket', completions: 245, attempts: 344, yards: 3691, tds: 32, ints: 5, rating: 172.8, percentile: 88 },
      { situation: 'Play action', completions: 87, attempts: 124, yards: 1342, tds: 14, ints: 2, rating: 181.4, percentile: 91 },
      { situation: 'No play action', completions: 200, attempts: 288, yards: 2861, tds: 24, ints: 4, rating: 163.2, percentile: 84 },
      { situation: 'Red zone', completions: 34, attempts: 42, yards: 218, tds: 18, ints: 0, rating: 182.4, percentile: 95 },
      { situation: 'Goal line', completions: 12, attempts: 14, yards: 48, tds: 8, ints: 0, rating: 158.3, percentile: 78 },
    ],
    'down-distance': [
      { situation: '1st down', completions: 98, attempts: 142, yards: 1542, tds: 14, ints: 2, rating: 168.4, percentile: 87 },
      { situation: '2nd & short', completions: 54, attempts: 72, yards: 682, tds: 8, ints: 1, rating: 172.1, percentile: 89 },
      { situation: '2nd & long', completions: 38, attempts: 64, yards: 524, tds: 4, ints: 2, rating: 142.6, percentile: 68 },
      { situation: '3rd & short', completions: 42, attempts: 52, yards: 312, tds: 5, ints: 0, rating: 178.2, percentile: 91 },
      { situation: '3rd & medium', completions: 32, attempts: 48, yards: 458, tds: 4, ints: 1, rating: 164.8, percentile: 82 },
      { situation: '3rd & long', completions: 23, attempts: 34, yards: 685, tds: 3, ints: 0, rating: 188.4, percentile: 94 },
    ],
    personnel: [
      { situation: '11 personnel', completions: 178, attempts: 256, yards: 2842, tds: 24, ints: 4, rating: 170.2, percentile: 88 },
      { situation: '12 personnel', completions: 64, attempts: 92, yards: 842, tds: 9, ints: 1, rating: 166.4, percentile: 84 },
      { situation: '10 personnel', completions: 32, attempts: 48, yards: 398, tds: 4, ints: 1, rating: 158.2, percentile: 76 },
      { situation: '21 personnel', completions: 13, attempts: 16, yards: 121, tds: 1, ints: 0, rating: 148.6, percentile: 72 },
    ],
    'opponent-tier': [
      { situation: 'Top 25', completions: 82, attempts: 124, yards: 1242, tds: 11, ints: 3, rating: 162.4, percentile: 81 },
      { situation: 'Ranked 26-50', completions: 98, attempts: 142, yards: 1568, tds: 14, ints: 2, rating: 168.8, percentile: 86 },
      { situation: 'Unranked P4', completions: 64, attempts: 88, yards: 942, tds: 8, ints: 1, rating: 172.2, percentile: 89 },
      { situation: 'G5', completions: 43, attempts: 58, yards: 451, tds: 5, ints: 0, rating: 178.6, percentile: 93 },
    ],
  };

  const tabLabels: Record<DeepTabId, string> = {
    situational: 'Situational',
    'down-distance': 'Down & Distance',
    personnel: 'Personnel',
    'opponent-tier': 'Opponent Tier',
  };

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
            SPLITS
          </h2>
          <p className="text-sm" style={{ color: 'oklch(0.6 0.02 250)' }}>
            Situational breakdowns · Awaiting minimum sample
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
            Split analysis requires 50+ attempts per situation. Check back after Week 3 for home/away, down/distance,
            and opponent tier breakdowns.
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
              width: '30%',
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
        <div className="splits-grid">
          {[1, 2, 3, 4].map((idx) => (
            <div
              key={idx}
              className="border"
              style={{
                background: 'oklch(0.20 0.01 250)',
                borderColor: 'oklch(0.28 0.01 250)',
                borderRadius: 'var(--radius-md)',
                height: '6rem',
              }}
            />
          ))}
        </div>
        <style>
          {`
            .splits-grid {
              display: grid;
              grid-template-columns: 1fr;
              gap: var(--space-4);
            }

            @container (min-width: 720px) {
              .splits-grid {
                grid-template-columns: repeat(2, 1fr);
              }
            }

            @container (min-width: 1200px) {
              .splits-grid {
                grid-template-columns: repeat(4, 1fr);
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
            SPLITS
          </h2>
          <p className="text-sm" style={{ color: 'oklch(0.6 0.02 250)' }}>
            Situational breakdowns · Load failed
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
            Could not load split data. Try refreshing the page.
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

  // Partial state: some splits below threshold
  const isPartial = variant === 'partial';
  const activeSplits = isPartial ? headlineSplits.slice(0, 2) : headlineSplits;

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
          SPLITS
        </h2>
        <p className="text-sm" style={{ color: 'oklch(0.6 0.02 250)' }}>
          {isPartial
            ? 'Situational breakdowns · Partial (2nd half and red zone data pending)'
            : 'Situational breakdowns · 30s headline / 5m deep dive'}
        </p>
      </div>

      {/* Headline split pairs */}
      <div className="splits-grid" style={{ marginBottom: 'var(--space-6)' }}>
        {activeSplits.map((split, idx) => (
          <div
            key={idx}
            className="border"
            style={{
              padding: 'var(--space-4)',
              background: 'oklch(0.20 0.01 250)',
              borderColor: 'oklch(0.28 0.01 250)',
              borderRadius: 'var(--radius-md)',
            }}
          >
            <div
              className="font-medium tracking-wider uppercase"
              style={{
                color: 'oklch(0.6 0.02 250)',
                letterSpacing: '0.08em',
                fontSize: 'var(--fs-meta)',
                marginBottom: 'var(--space-3)',
              }}
            >
              {split.label}
            </div>
            <div style={{ display: 'flex', gap: 'var(--space-4)' }}>
              {/* Left side */}
              <div style={{ flex: 1 }}>
                <div className="text-xs" style={{ color: 'oklch(0.6 0.02 250)', marginBottom: 'var(--space-1)' }}>
                  {split.leftLabel}
                </div>
                <div
                  className="font-semibold tabular-nums"
                  style={{
                    fontFamily: 'var(--font-display)',
                    color: 'oklch(0.95 0.01 250)',
                    fontSize: 'var(--fs-h2)',
                    marginBottom: 'var(--space-2)',
                  }}
                >
                  {split.leftValue}
                </div>
                <div
                  className="relative rounded-full"
                  style={{
                    height: 'var(--space-2)',
                    background: 'oklch(0.25 0.01 250)',
                  }}
                  role="meter"
                  aria-label={`${split.leftLabel}: ${split.leftPercentile}th percentile`}
                  aria-valuenow={split.leftPercentile}
                  aria-valuemin={0}
                  aria-valuemax={100}
                >
                  <div
                    className="absolute inset-y-0 left-0 rounded-full"
                    style={{
                      width: `${split.leftPercentile}%`,
                      background:
                        split.leftPercentile >= 90
                          ? 'var(--percentile-100)'
                          : split.leftPercentile >= 75
                            ? 'var(--percentile-90)'
                            : 'var(--percentile-75)',
                      transition: 'width var(--motion-data-entry)',
                    }}
                  />
                </div>
              </div>

              {/* Divider */}
              <div style={{ width: '1px', background: 'oklch(0.28 0.01 250)' }} />

              {/* Right side */}
              <div style={{ flex: 1 }}>
                <div className="text-xs" style={{ color: 'oklch(0.6 0.02 250)', marginBottom: 'var(--space-1)' }}>
                  {split.rightLabel}
                </div>
                <div
                  className="font-semibold tabular-nums"
                  style={{
                    fontFamily: 'var(--font-display)',
                    color: 'oklch(0.95 0.01 250)',
                    fontSize: 'var(--fs-h2)',
                    marginBottom: 'var(--space-2)',
                  }}
                >
                  {split.rightValue}
                </div>
                <div
                  className="relative rounded-full"
                  style={{
                    height: 'var(--space-2)',
                    background: 'oklch(0.25 0.01 250)',
                  }}
                  role="meter"
                  aria-label={`${split.rightLabel}: ${split.rightPercentile}th percentile`}
                  aria-valuenow={split.rightPercentile}
                  aria-valuemin={0}
                  aria-valuemax={100}
                >
                  <div
                    className="absolute inset-y-0 left-0 rounded-full"
                    style={{
                      width: `${split.rightPercentile}%`,
                      background:
                        split.rightPercentile >= 90
                          ? 'var(--percentile-100)'
                          : split.rightPercentile >= 75
                            ? 'var(--percentile-90)'
                            : 'var(--percentile-75)',
                      transition: 'width var(--motion-data-entry)',
                    }}
                  />
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Deep dive toggle */}
      <button
        type="button"
        className="text-sm font-semibold"
        style={{
          padding: 'var(--space-3) var(--space-4)',
          background: isDrawerOpen ? 'oklch(0.3 0.01 250)' : 'oklch(0.25 0.01 250)',
          color: 'oklch(0.95 0.01 250)',
          border: 'none',
          borderRadius: 'var(--radius-sm)',
          transition: 'background var(--motion-state)',
          minHeight: '44px',
        }}
        onClick={() => setIsDrawerOpen(!isDrawerOpen)}
        aria-expanded={isDrawerOpen}
      >
        {isDrawerOpen ? 'Hide deep splits' : 'Show deep splits →'}
      </button>

      {/* Deep splits drawer (progressive disclosure) */}
      {isDrawerOpen && (
        <div
          style={{
            marginTop: 'var(--space-8)',
            animation: 'slideDown var(--motion-reveal) ease-out',
          }}
        >
          {/* Tab bar */}
          <div className="flex flex-wrap" style={{ gap: 'var(--space-2)', marginBottom: 'var(--space-6)' }}>
            {(Object.keys(tabLabels) as DeepTabId[]).map((tabId) => (
              <button
                key={tabId}
                type="button"
                className="text-xs font-semibold tracking-wider uppercase"
                style={{
                  padding: 'var(--space-3) var(--space-5)',
                  background: activeTab === tabId ? 'oklch(0.3 0.01 250)' : 'transparent',
                  color: activeTab === tabId ? 'oklch(0.95 0.01 250)' : 'oklch(0.6 0.02 250)',
                  border: activeTab === tabId ? 'none' : '1px solid oklch(0.28 0.01 250)',
                  letterSpacing: '0.08em',
                  borderRadius: '999px',
                  transition: 'background var(--motion-state), color var(--motion-state)',
                  minHeight: '44px',
                }}
                onClick={() => setActiveTab(tabId)}
                aria-pressed={activeTab === tabId}
              >
                {tabLabels[tabId]}
              </button>
            ))}
          </div>

          {/* Deep splits table */}
          <div
            className="border"
            style={{
              background: 'oklch(0.20 0.01 250)',
              borderColor: 'oklch(0.28 0.01 250)',
              borderRadius: 'var(--radius-md)',
              overflow: 'hidden',
            }}
          >
            <div className="splits-table">
              {/* Header row */}
              <div className="splits-table-header">
                <div className="splits-table-cell">Situation</div>
                <div className="splits-table-cell">Comp</div>
                <div className="splits-table-cell">Att</div>
                <div className="splits-table-cell">Yds</div>
                <div className="splits-table-cell">TD</div>
                <div className="splits-table-cell">Int</div>
                <div className="splits-table-cell">Rating</div>
                <div className="splits-table-cell">Pct</div>
              </div>

              {/* Data rows */}
              {deepSplitsData[activeTab].map((row, idx) => (
                <div key={idx} className="splits-table-row">
                  <div className="splits-table-cell" style={{ color: 'oklch(0.95 0.01 250)' }}>
                    {row.situation}
                  </div>
                  <div className="splits-table-cell tabular-nums">{row.completions}</div>
                  <div className="splits-table-cell tabular-nums">{row.attempts}</div>
                  <div className="splits-table-cell tabular-nums">{row.yards}</div>
                  <div className="splits-table-cell tabular-nums">{row.tds}</div>
                  <div className="splits-table-cell tabular-nums">{row.ints}</div>
                  <div className="splits-table-cell tabular-nums">{row.rating}</div>
                  <div className="splits-table-cell">
                    <div
                      className="text-xs font-semibold tabular-nums"
                      style={{
                        padding: 'var(--space-1) var(--space-2)',
                        background:
                          row.percentile >= 90
                            ? 'var(--percentile-100)'
                            : row.percentile >= 75
                              ? 'var(--percentile-90)'
                              : 'var(--percentile-75)',
                        color: 'oklch(0.18 0.01 250)',
                        borderRadius: '999px',
                        display: 'inline-block',
                      }}
                    >
                      {row.percentile}
                      <span style={{ fontSize: '9px' }}>th</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      <style>
        {`
          .splits-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: var(--space-4);
          }

          @container (min-width: 720px) {
            .splits-grid {
              grid-template-columns: repeat(2, 1fr);
            }
          }

          @container (min-width: 1200px) {
            .splits-grid {
              grid-template-columns: repeat(4, 1fr);
            }
          }

          @keyframes slideDown {
            from {
              opacity: 0;
              transform: translateY(-8px);
            }
            to {
              opacity: 1;
              transform: translateY(0);
            }
          }

          .splits-table {
            display: grid;
            grid-template-columns: 2fr repeat(7, 1fr);
            font-size: var(--fs-meta);
          }

          .splits-table-header {
            display: contents;
          }

          .splits-table-header .splits-table-cell {
            padding: var(--space-3);
            background: oklch(0.22 0.01 250);
            color: oklch(0.6 0.02 250);
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-size: 10px;
            border-bottom: 1px solid oklch(0.28 0.01 250);
          }

          .splits-table-row {
            display: contents;
          }

          .splits-table-row .splits-table-cell {
            padding: var(--space-3);
            color: oklch(0.7 0.02 250);
            border-bottom: 1px solid oklch(0.25 0.01 250);
          }

          .splits-table-row:last-child .splits-table-cell {
            border-bottom: none;
          }

          @container (max-width: 720px) {
            .splits-table {
              grid-template-columns: 1.5fr repeat(7, 0.8fr);
              font-size: 11px;
            }

            .splits-table-cell {
              padding: var(--space-2) !important;
            }
          }
        `}
      </style>
    </div>
  );
}
