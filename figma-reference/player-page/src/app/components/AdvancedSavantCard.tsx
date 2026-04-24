// Advanced Savant Card — 5m tier
// Baseball Savant tribute: 6 advanced metrics with percentile bars
// Cohort filter: P4 / G5 / All-FBS

import { useState } from 'react';

type StateVariant = 'full' | 'empty' | 'loading' | 'partial' | 'error';
type CohortId = 'p4' | 'g5' | 'all-fbs';

interface MetricRow {
  label: string;
  value: number;
  percentile: number;
  interpretation: string;
  rank?: string;
}

interface CohortData {
  id: CohortId;
  label: string;
  description: string;
  metrics: MetricRow[];
}

export default function AdvancedSavantCard({
  variant = 'full',
  cohort: externalCohort,
  onCohortChange,
}: {
  variant?: StateVariant;
  cohort?: CohortId;
  onCohortChange?: (cohort: CohortId) => void;
}) {
  const [internalCohort, setInternalCohort] = useState<CohortId>('p4');
  const activeCohort = externalCohort ?? internalCohort;

  const handleCohortChange = (cohort: CohortId) => {
    if (onCohortChange) {
      onCohortChange(cohort);
    } else {
      setInternalCohort(cohort);
    }
  };

  const cohortData: Record<CohortId, CohortData> = {
    p4: {
      id: 'p4',
      label: 'P4',
      description: 'P4 QBs · Week 12 update',
      metrics: [
        {
          label: 'EPA/dropback',
          value: 0.42,
          percentile: 91,
          rank: '#12 of 58',
          interpretation: 'Elite efficiency — every pass attempt adds +0.42 expected points vs P4 average of +0.18',
        },
        {
          label: 'CPOE',
          value: 8.2,
          percentile: 88,
          rank: '#15 of 58',
          interpretation: 'Completion % over expected — beats the model by 8.2 points after factoring target depth and pressure',
        },
        {
          label: 'Pressure-to-sack %',
          value: 12.1,
          percentile: 84,
          rank: '#18 of 58',
          interpretation: 'Pocket awareness — only 12% of pressures turn into sacks, top-15 nationally',
        },
        {
          label: 'Off-target %',
          value: 11.4,
          percentile: 86,
          rank: '#14 of 58',
          interpretation: 'Ball placement precision — 88.6% of throws charted as on-target or better',
        },
        {
          label: 'Under-pressure EPA',
          value: 0.38,
          percentile: 92,
          rank: '#10 of 58',
          interpretation: 'Signature metric — maintains elite EPA even when blitzed or flushed from the pocket',
        },
        {
          label: 'Third-down EPA',
          value: 0.51,
          percentile: 89,
          rank: '#13 of 58',
          interpretation: 'Clutch performance — converts 3rd downs at a +0.51 EPA rate, money-down specialist',
        },
      ],
    },
    g5: {
      id: 'g5',
      label: 'G5',
      description: 'G5 QBs · Week 12 update',
      metrics: [
        {
          label: 'EPA/dropback',
          value: 0.42,
          percentile: 96,
          rank: '#3 of 35',
          interpretation: 'Dominant efficiency — +0.42 EPA/dropback ranks top-3 among G5 starters, exceeds conference average by 0.28',
        },
        {
          label: 'CPOE',
          value: 8.2,
          percentile: 94,
          rank: '#4 of 35',
          interpretation: 'Model-beating accuracy — 8.2-point CPOE places in 94th percentile vs G5 cohort',
        },
        {
          label: 'Pressure-to-sack %',
          value: 12.1,
          percentile: 91,
          rank: '#5 of 35',
          interpretation: 'Elite pocket navigation — 12.1% sack rate under pressure ranks top-5 among G5 QBs',
        },
        {
          label: 'Off-target %',
          value: 11.4,
          percentile: 93,
          rank: '#4 of 35',
          interpretation: 'Precision passing — 88.6% on-target rate ranks 4th among G5 starters',
        },
        {
          label: 'Under-pressure EPA',
          value: 0.38,
          percentile: 97,
          rank: '#2 of 35',
          interpretation: 'Signature stat — #2 in G5 for EPA under pressure, elite composure against blitz',
        },
        {
          label: 'Third-down EPA',
          value: 0.51,
          percentile: 95,
          rank: '#3 of 35',
          interpretation: 'Money-down mastery — +0.51 3rd-down EPA ranks top-3 in G5, converts at elite rate',
        },
      ],
    },
    'all-fbs': {
      id: 'all-fbs',
      label: 'All FBS',
      description: 'All FBS QBs · Week 12 update',
      metrics: [
        {
          label: 'EPA/dropback',
          value: 0.42,
          percentile: 89,
          rank: '#24 of 93',
          interpretation: 'Top-quartile efficiency — +0.42 EPA/dropback ranks 24th among all FBS starters',
        },
        {
          label: 'CPOE',
          value: 8.2,
          percentile: 86,
          rank: '#29 of 93',
          interpretation: 'Model-beating accuracy — 8.2 CPOE ranks in 86th percentile nationally',
        },
        {
          label: 'Pressure-to-sack %',
          value: 12.1,
          percentile: 82,
          rank: '#32 of 93',
          interpretation: 'Solid pocket awareness — 12.1% sack rate under pressure, top-35 nationally',
        },
        {
          label: 'Off-target %',
          value: 11.4,
          percentile: 84,
          rank: '#28 of 93',
          interpretation: 'Precise passing — 88.6% on-target rate ranks top-30 among FBS starters',
        },
        {
          label: 'Under-pressure EPA',
          value: 0.38,
          percentile: 90,
          rank: '#21 of 93',
          interpretation: 'Elite under pressure — +0.38 EPA when pressured ranks top-25 nationally',
        },
        {
          label: 'Third-down EPA',
          value: 0.51,
          percentile: 87,
          rank: '#26 of 93',
          interpretation: 'Clutch performer — +0.51 3rd-down EPA ranks top-30 among FBS QBs',
        },
      ],
    },
  };

  const partialMetrics: MetricRow[] = [
    {
      label: 'EPA/dropback',
      value: 0.42,
      percentile: 91,
      interpretation: 'Elite efficiency — every pass attempt adds +0.42 expected points vs P4 average of +0.18',
    },
    {
      label: 'CPOE',
      value: 8.2,
      percentile: 88,
      interpretation: 'Completion % over expected — beats the model by 8.2 points after factoring target depth and pressure',
    },
    {
      label: 'Pressure-to-sack %',
      value: 12.1,
      percentile: 84,
      interpretation: 'Pocket awareness — only 12% of pressures turn into sacks, top-15 nationally',
    },
    {
      label: 'Off-target %',
      value: 0,
      percentile: 0,
      interpretation: 'Charting data incomplete — awaiting film review from last 2 games',
    },
    {
      label: 'Under-pressure EPA',
      value: 0,
      percentile: 0,
      interpretation: 'Sample size below threshold — need 15+ pressured dropbacks for publication',
    },
    {
      label: 'Third-down EPA',
      value: 0.51,
      percentile: 89,
      interpretation: 'Clutch performance — converts 3rd downs at a +0.51 EPA rate, money-down specialist',
    },
  ];

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
            ADVANCED SAVANT
          </h2>
          <p className="text-sm" style={{ color: 'oklch(0.6 0.02 250)' }}>
            Metrics unavailable · Awaiting play-by-play data
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
            Advanced metrics require play-by-play tracking and pressure charting. Check back after Week 3 when sample
            sizes reach publication threshold.
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
              width: '50%',
              background: 'oklch(0.25 0.01 250)',
              borderRadius: 'var(--radius-md)',
              marginBottom: 'var(--space-2)',
            }}
          />
          <div
            style={{
              height: '1rem',
              width: '35%',
              background: 'oklch(0.22 0.01 250)',
              borderRadius: 'var(--radius-sm)',
            }}
          />
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          {[1, 2, 3, 4, 5, 6].map((idx) => (
            <div key={idx}>
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
                  height: 'var(--space-3)',
                  width: '100%',
                  background: 'oklch(0.25 0.01 250)',
                  borderRadius: '999px',
                }}
              />
            </div>
          ))}
        </div>
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
            ADVANCED SAVANT
          </h2>
          <p className="text-sm" style={{ color: 'oklch(0.6 0.02 250)' }}>
            Metrics unavailable · Load failed
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
            Could not retrieve advanced metrics. Try refreshing the page.
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
  const isPartial = variant === 'partial';
  const activeMetrics = isPartial ? partialMetrics : cohortData[activeCohort].metrics;
  const activeDescription = isPartial ? 'P4 QBs · Week 12 update · Partial (2 metrics below threshold)' : cohortData[activeCohort].description;

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
          ADVANCED METRICS
        </div>
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
          SAVANT CARD
        </h2>
        <p className="text-sm" style={{ color: 'oklch(0.6 0.02 250)', marginBottom: 'var(--space-4)' }}>
          {activeDescription}
        </p>

        {/* Cohort filter pills */}
        {!isPartial && (
          <div className="flex flex-wrap" style={{ gap: 'var(--space-2)' }}>
            {(Object.keys(cohortData) as CohortId[]).map((cohortId) => {
              const cohort = cohortData[cohortId];
              const isActive = activeCohort === cohortId;
              return (
                <button
                  key={cohortId}
                  type="button"
                  onClick={() => handleCohortChange(cohortId)}
                  aria-pressed={isActive}
                  className="text-xs font-semibold tracking-wider uppercase"
                  style={{
                    padding: 'var(--space-3) var(--space-5)',
                    background: isActive ? 'oklch(0.3 0.01 250)' : 'transparent',
                    color: isActive ? 'oklch(0.95 0.01 250)' : 'oklch(0.6 0.02 250)',
                    border: isActive ? 'none' : '1px solid oklch(0.28 0.01 250)',
                    letterSpacing: '0.08em',
                    borderRadius: '999px',
                    transition: 'background var(--motion-state), color var(--motion-state)',
                    minHeight: '44px',
                  }}
                >
                  {cohort.label}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Metrics */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
        {activeMetrics.map((metric, idx) => {
          const isValid = metric.value > 0 && metric.percentile > 0;
          return (
            <div key={idx}>
              <div className="flex items-baseline justify-between" style={{ marginBottom: 'var(--space-2)' }}>
                <div
                  className="font-medium tracking-wider uppercase"
                  style={{
                    color: 'oklch(0.7 0.02 250)',
                    letterSpacing: '0.08em',
                    fontSize: 'var(--fs-meta)',
                  }}
                >
                  {metric.label}
                </div>
                {isValid && (
                  <div className="flex items-baseline" style={{ gap: 'var(--space-2)' }}>
                    <span
                      className="font-semibold tabular-nums"
                      style={{
                        fontFamily: 'var(--font-display)',
                        color: 'oklch(0.95 0.01 250)',
                        fontSize: 'var(--fs-h2)',
                      }}
                    >
                      {metric.value}
                    </span>
                    {metric.rank && (
                      <span className="text-xs" style={{ color: 'oklch(0.6 0.02 250)' }}>
                        {metric.rank}
                      </span>
                    )}
                    <span
                      className="text-xs font-semibold tabular-nums"
                      style={{
                        color:
                          metric.percentile >= 90
                            ? 'var(--percentile-100)'
                            : metric.percentile >= 75
                              ? 'var(--percentile-90)'
                              : 'var(--percentile-75)',
                      }}
                      aria-label={`${metric.percentile}th percentile`}
                    >
                      {metric.percentile}
                      <span style={{ fontSize: '9px' }}>th</span>
                    </span>
                  </div>
                )}
              </div>

              {/* Percentile bar */}
              {isValid ? (
                <div
                  className="relative rounded-full"
                  style={{
                    height: 'var(--space-3)',
                    background: 'oklch(0.25 0.01 250)',
                    marginBottom: 'var(--space-2)',
                  }}
                  role="meter"
                  aria-label={`${metric.label}: ${metric.percentile}th percentile`}
                  aria-valuenow={metric.percentile}
                  aria-valuemin={0}
                  aria-valuemax={100}
                >
                  <div
                    className="absolute inset-y-0 left-0 rounded-full"
                    style={{
                      width: `${metric.percentile}%`,
                      background:
                        metric.percentile >= 90
                          ? 'linear-gradient(90deg, var(--percentile-75) 0%, var(--percentile-100) 100%)'
                          : metric.percentile >= 75
                            ? 'linear-gradient(90deg, var(--percentile-50) 0%, var(--percentile-90) 100%)'
                            : 'var(--percentile-75)',
                      transition: 'width var(--motion-data-entry)',
                    }}
                  />
                </div>
              ) : (
                <div
                  className="relative rounded-full"
                  style={{
                    height: 'var(--space-3)',
                    background: 'oklch(0.25 0.01 250)',
                    marginBottom: 'var(--space-2)',
                  }}
                />
              )}

              {/* Interpretation */}
              <p className="text-xs leading-relaxed" style={{ color: isValid ? 'oklch(0.7 0.02 250)' : 'oklch(0.6 0.02 250)' }}>
                {metric.interpretation}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
