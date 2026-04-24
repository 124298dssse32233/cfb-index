// The Room on [Player] — 30s tier
// Fan sentiment module: belief dial, cohort breakdown, top take, confidence, trajectory

import { useState } from 'react';

type StateVariant = 'full' | 'empty' | 'loading' | 'partial' | 'error';
type CohortId = 'own' | 'rival' | 'national' | 'media';

interface CohortData {
  id: CohortId;
  label: string;
  score: number;
  sample: number;
  confidence: string;
  topTake: string;
  takeCount: number;
  trajectory: number[];
}

export default function TheRoomOnPlayer({
  variant = 'full',
  initialCohort,
  onCohortChange,
}: {
  variant?: StateVariant;
  initialCohort?: CohortId;
  onCohortChange?: (cohort: CohortId) => void;
}) {
  const cohortData: Record<CohortId, CohortData> = {
    own: {
      id: 'own',
      label: 'Notre Dame fans',
      score: 78,
      sample: 1847,
      confidence: 'High',
      topTake:
        "Carr's pocket presence is NFL-caliber. The way he steps up into pressure and delivers strikes downfield — that's not coachable, that's instinct.",
      takeCount: 342,
      trajectory: [58, 62, 64, 68, 72, 76, 78],
    },
    rival: {
      id: 'rival',
      label: 'Rival fans',
      score: 54,
      sample: 923,
      confidence: 'Medium',
      topTake:
        "He's good, but he hasn't faced a real defense yet. Wait until he plays a top-10 pass rush before crowning him.",
      takeCount: 178,
      trajectory: [48, 52, 50, 51, 53, 55, 54],
    },
    national: {
      id: 'national',
      label: 'National',
      score: 66,
      sample: 3214,
      confidence: 'High',
      topTake:
        'Carr is the real deal — best pure passer in this draft class. The NFL upside is obvious if he can stay healthy.',
      takeCount: 521,
      trajectory: [60, 62, 63, 64, 65, 66, 66],
    },
    media: {
      id: 'media',
      label: 'Media',
      score: 71,
      sample: 412,
      confidence: 'High',
      topTake:
        'The metrics back up the tape — Carr is playing at an All-American level. The question is whether he can sustain it under playoff pressure.',
      takeCount: 89,
      trajectory: [65, 68, 69, 70, 71, 72, 71],
    },
  };

  const [internalCohortId, setInternalCohortId] = useState<CohortId>('own');
  const activeCohortId = initialCohort ?? internalCohortId;
  const activeCohort = cohortData[activeCohortId];

  const handleCohortChange = (cohortId: CohortId) => {
    if (onCohortChange) {
      onCohortChange(cohortId);
    } else {
      setInternalCohortId(cohortId);
    }
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
            THE ROOM ON CARR
          </h2>
          <p className="text-sm" style={{ color: 'oklch(0.6 0.02 250)' }}>
            Fan sentiment · Awaiting signal
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
            Belief tracking requires 100+ social mentions per cohort. Check back after Week 1 when the sample reaches
            publication threshold.
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
        <div className="flex flex-wrap" style={{ gap: 'var(--space-2)', marginBottom: 'var(--space-6)' }}>
          {[1, 2, 3, 4].map((idx) => (
            <div
              key={idx}
              style={{
                height: '2.75rem',
                width: '6rem',
                background: 'oklch(0.25 0.01 250)',
                borderRadius: '999px',
              }}
            />
          ))}
        </div>
        <div className="room-content-grid">
          <div>
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
              style={{
                height: 'var(--space-4)',
                width: '100%',
                background: 'oklch(0.25 0.01 250)',
                borderRadius: '999px',
                marginBottom: 'var(--space-4)',
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
              className="border"
              style={{
                background: 'oklch(0.20 0.01 250)',
                borderColor: 'oklch(0.28 0.01 250)',
                borderRadius: 'var(--radius-md)',
                height: '8rem',
              }}
            />
          </div>
        </div>
        <style>
          {`
            .room-content-grid {
              display: grid;
              grid-template-columns: 1fr;
              gap: var(--space-8);
            }

            @container (min-width: 720px) {
              .room-content-grid {
                grid-template-columns: 1fr 1.5fr;
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
            THE ROOM ON CARR
          </h2>
          <p className="text-sm" style={{ color: 'oklch(0.6 0.02 250)' }}>
            Fan sentiment · Load failed
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
            Could not retrieve sentiment data. Check your connection and try again.
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

  // Partial state
  const isPartial = variant === 'partial';

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
          THE ROOM ON CARR
        </h2>
        <p className="text-sm" style={{ color: 'oklch(0.6 0.02 250)' }}>
          {isPartial
            ? 'Fan sentiment · Belief dial · Cohort breakdown · Media cohort sample below threshold'
            : 'Fan sentiment · Belief dial · Cohort breakdown · 30-second read'}
        </p>
      </div>

      {/* Cohort filter pills */}
      <div className="flex flex-wrap" style={{ gap: 'var(--space-2)', marginBottom: 'var(--space-6)' }}>
        {(Object.keys(cohortData) as CohortId[]).map((cohortId) => {
          const cohort = cohortData[cohortId];
          const isActive = cohortId === activeCohortId;
          const isDisabled = isPartial && cohortId === 'media';
          return (
            <button
              key={cohortId}
              type="button"
              className="text-xs font-semibold tracking-wider uppercase"
              style={{
                padding: 'var(--space-3) var(--space-5)',
                background: isActive ? 'oklch(0.3 0.01 250)' : 'transparent',
                color: isDisabled
                  ? 'oklch(0.4 0.02 250)'
                  : isActive
                    ? 'oklch(0.95 0.01 250)'
                    : 'oklch(0.6 0.02 250)',
                border: isActive ? 'none' : '1px solid oklch(0.28 0.01 250)',
                letterSpacing: '0.08em',
                borderRadius: '999px',
                transition: 'background var(--motion-state), color var(--motion-state)',
                minHeight: '44px',
                cursor: isDisabled ? 'not-allowed' : 'pointer',
                opacity: isDisabled ? 0.5 : 1,
              }}
              onClick={() => !isDisabled && handleCohortChange(cohortId)}
              aria-pressed={isActive}
              aria-label={`Filter by ${cohort.label}: ${cohort.score} percent belief`}
              disabled={isDisabled}
            >
              {cohort.label}
            </button>
          );
        })}
      </div>

      {/* Main content grid */}
      <div className="room-content-grid" style={{ marginBottom: 'var(--space-8)' }}>
        {/* Left: Belief dial + metadata */}
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
            BELIEF METER
          </div>

          {/* Belief dial (reuse primitive pattern) */}
          <div
            className="relative rounded-full overflow-hidden"
            style={{
              height: 'var(--space-4)',
              background: 'oklch(0.25 0.01 250)',
              transition: 'background var(--motion-state)',
              marginBottom: 'var(--space-4)',
            }}
            role="meter"
            aria-label={`${activeCohort.label} belief: ${activeCohort.score} percent`}
            aria-valuenow={activeCohort.score}
            aria-valuemin={0}
            aria-valuemax={100}
          >
            <div
              className="absolute inset-y-0 left-0 rounded-full"
              style={{
                width: `${activeCohort.score}%`,
                background:
                  activeCohort.score >= 70
                    ? 'linear-gradient(90deg, var(--belief-neutral) 0%, var(--belief-positive) 100%)'
                    : activeCohort.score >= 40
                      ? 'var(--belief-neutral)'
                      : 'linear-gradient(90deg, var(--belief-negative) 0%, var(--belief-neutral) 100%)',
                transition: 'width var(--motion-data-entry)',
              }}
            />
            <div
              className="absolute top-1/2 -translate-y-1/2 rounded-sm"
              style={{
                left: `${activeCohort.score}%`,
                width: '0.25rem',
                height: 'var(--space-6)',
                background: 'oklch(0.95 0.01 250)',
                transition: 'left var(--motion-data-entry)',
              }}
            />
          </div>

          {/* Score + archetype */}
          <div style={{ marginBottom: 'var(--space-6)' }}>
            <div
              className="leading-none tabular-nums"
              style={{
                fontFamily: 'var(--font-display)',
                color: activeCohort.score >= 70 ? 'var(--belief-positive)' : 'oklch(0.95 0.01 250)',
                fontWeight: 700,
                fontSize: 'var(--fs-h1)',
                marginBottom: 'var(--space-2)',
              }}
            >
              {activeCohort.score}
            </div>
            <div className="text-sm" style={{ color: 'oklch(0.7 0.02 250)' }}>
              {activeCohort.score >= 70
                ? 'Grounded Optimism'
                : activeCohort.score >= 40
                  ? 'Mixed Sentiment'
                  : 'Skeptical'}
            </div>
          </div>

          {/* Confidence + sample size */}
          <div
            className="border"
            style={{
              padding: 'var(--space-3)',
              background: 'oklch(0.20 0.01 250)',
              borderColor: 'oklch(0.28 0.01 250)',
              borderRadius: 'var(--radius-md)',
              display: 'flex',
              flexDirection: 'column',
              gap: 'var(--space-2)',
            }}
          >
            <div className="flex items-center justify-between text-xs">
              <span style={{ color: 'oklch(0.6 0.02 250)' }}>Sample</span>
              <span
                className="font-semibold tabular-nums"
                style={{ color: 'oklch(0.95 0.01 250)' }}
                aria-label={`Sample size: ${activeCohort.sample.toLocaleString()} mentions`}
              >
                {activeCohort.sample.toLocaleString()} mentions
              </span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span style={{ color: 'oklch(0.6 0.02 250)' }}>Confidence</span>
              <span
                className="font-semibold"
                style={{ color: activeCohort.confidence === 'High' ? 'var(--belief-positive)' : 'var(--belief-neutral)' }}
                aria-label={`Confidence level: ${activeCohort.confidence.toLowerCase()}`}
              >
                {activeCohort.confidence}
              </span>
            </div>
          </div>
        </div>

        {/* Right: Top quoted take + trajectory */}
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
            TOP TAKE
          </div>

          {/* Quoted take card */}
          <div
            className="border"
            style={{
              padding: 'var(--space-6)',
              background: 'oklch(0.20 0.01 250)',
              borderColor: 'oklch(0.28 0.01 250)',
              borderRadius: 'var(--radius-md)',
              boxShadow: 'var(--elevation-1)',
              marginBottom: 'var(--space-6)',
            }}
          >
            <p
              className="leading-relaxed"
              style={{
                color: 'oklch(0.95 0.01 250)',
                fontSize: 'var(--fs-body)',
                marginBottom: 'var(--space-3)',
              }}
            >
              "{activeCohort.topTake}"
            </p>
            <div className="text-xs" style={{ color: 'oklch(0.6 0.02 250)' }}>
              Most-quoted sentiment · {activeCohort.takeCount} similar takes
            </div>
          </div>

          {/* Trajectory spark (6-week belief history) */}
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
              6-WEEK TRAJECTORY
            </div>
            <div className="relative">
              <svg width="100%" height="60" viewBox="0 0 400 60" className="w-full">
                <defs>
                  <linearGradient id="beliefGradient" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0%" stopColor="var(--belief-neutral)" />
                    <stop offset="100%" stopColor="var(--belief-positive)" />
                  </linearGradient>
                </defs>
                {/* Baseline at 50% */}
                <line x1="0" y1="30" x2="400" y2="30" stroke="oklch(0.3 0.01 250)" strokeDasharray="4,4" strokeWidth="1" />
                {/* Trajectory line */}
                <polyline
                  points={activeCohort.trajectory
                    .map((val, idx) => {
                      const x = (idx / (activeCohort.trajectory.length - 1)) * 400;
                      const y = 60 - (val / 100) * 60;
                      return `${x},${y}`;
                    })
                    .join(' ')}
                  fill="none"
                  stroke={activeCohort.score >= 70 ? 'url(#beliefGradient)' : 'var(--belief-neutral)'}
                  strokeWidth="2.5"
                />
                <circle
                  cx={400}
                  cy={60 - (activeCohort.trajectory[activeCohort.trajectory.length - 1] / 100) * 60}
                  r="4"
                  fill={activeCohort.score >= 70 ? 'var(--belief-positive)' : 'var(--belief-neutral)'}
                />
              </svg>
              <div
                className="flex justify-between text-xs"
                style={{ marginTop: 'var(--space-1)', color: 'oklch(0.5 0.02 250)' }}
              >
                <span style={{ fontSize: 'var(--fs-meta)' }}>Wk 6</span>
                <span style={{ fontSize: 'var(--fs-meta)' }}>Wk 11</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <style>
        {`
          .room-content-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: var(--space-8);
          }

          @container (min-width: 720px) {
            .room-content-grid {
              grid-template-columns: 1fr 1.5fr;
            }
          }
        `}
      </style>
    </div>
  );
}
