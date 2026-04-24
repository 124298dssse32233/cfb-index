// Supporting Cast — deep tier
// Team context that explains the numbers: OL protection, top receivers, play-caller, defensive coordinator

type StateVariant = 'full' | 'empty' | 'loading' | 'partial' | 'error';

interface Receiver {
  name: string;
  targets: number;
  catches: number;
  yards: number;
  tds: number;
  percentile: number;
}

export default function SupportingCast({ variant = 'full' }: { variant?: StateVariant }) {
  const supportingData = {
    olProtection: {
      grade: 82.4,
      rank: 8,
      percentile: 88,
      narrative: 'Elite pass protection unit — allows pressure on just 18.2% of dropbacks, 8th-best nationally.',
    },
    topReceivers: [
      { name: 'Jaden Greathouse', targets: 98, catches: 68, yards: 1124, tds: 12, percentile: 86 },
      { name: 'Beaux Collins', targets: 82, catches: 54, yards: 892, tds: 9, percentile: 78 },
      { name: 'Jordan Faison', targets: 64, catches: 42, yards: 658, tds: 7, percentile: 72 },
    ],
    playCaller: {
      name: 'Mike Denbrock',
      role: 'Offensive Coordinator',
      scheme: 'Pro-style, heavy play-action',
      narrative: '2nd season at ND. Former LSU OC. Favors 11 personnel (3WR) and deep shots off PA.',
    },
    defCoordinator: {
      name: 'Al Golden',
      role: 'Defensive Coordinator',
      scheme: '3-4 base, multiple fronts',
      narrative: "3rd season at ND. Runs a bend-don't-break scheme that forces QBs into check-downs.",
    },
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
            SUPPORTING CAST
          </h2>
          <p className="text-sm" style={{ color: 'oklch(0.6 0.02 250)' }}>
            Team context · Awaiting roster data
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
            Supporting Cast context requires team roster and depth chart data. Check back when the official roster is
            published.
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
              width: '40%',
              background: 'oklch(0.25 0.01 250)',
              borderRadius: 'var(--radius-md)',
              marginBottom: 'var(--space-2)',
            }}
          />
          <div
            style={{
              height: '1rem',
              width: '30%',
              background: 'oklch(0.22 0.01 250)',
              borderRadius: 'var(--radius-sm)',
            }}
          />
        </div>
        <div className="cast-grid">
          {[1, 2, 3, 4, 5, 6].map((idx) => (
            <div
              key={idx}
              className="border"
              style={{
                background: 'oklch(0.20 0.01 250)',
                borderColor: 'oklch(0.28 0.01 250)',
                borderRadius: 'var(--radius-md)',
                height: '8rem',
              }}
            />
          ))}
        </div>
        <style>
          {`
            .cast-grid {
              display: grid;
              grid-template-columns: 1fr;
              gap: var(--space-4);
            }

            @container (min-width: 720px) {
              .cast-grid {
                grid-template-columns: repeat(2, 1fr);
              }
            }

            @container (min-width: 1200px) {
              .cast-grid {
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
            SUPPORTING CAST
          </h2>
          <p className="text-sm" style={{ color: 'oklch(0.6 0.02 250)' }}>
            Team context · Load failed
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
            Could not load supporting cast data. Try refreshing the page.
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

  // Partial state: OC and DC data missing
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
          SUPPORTING CAST
        </h2>
        <p className="text-sm" style={{ color: 'oklch(0.6 0.02 250)' }}>
          {isPartial
            ? 'Team context · Partial (coordinator data pending)'
            : 'Team context · OL protection · Top receivers · Coordinators'}
        </p>
      </div>

      {/* Reference cards grid */}
      <div className="cast-grid">
        {/* OL Protection */}
        <div
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
              marginBottom: 'var(--space-2)',
            }}
          >
            OL PASS PROTECTION
          </div>
          <div
            className="font-semibold tabular-nums"
            style={{
              fontFamily: 'var(--font-display)',
              color: 'var(--percentile-90)',
              fontSize: 'var(--fs-h1)',
              marginBottom: 'var(--space-2)',
            }}
          >
            {supportingData.olProtection.grade}
          </div>
          <p className="text-sm leading-relaxed" style={{ color: 'oklch(0.7 0.02 250)' }}>
            {supportingData.olProtection.narrative}
          </p>
        </div>

        {/* Top 3 Receivers */}
        {supportingData.topReceivers.map((receiver, idx) => (
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
                marginBottom: 'var(--space-2)',
              }}
            >
              WR {idx + 1}
            </div>
            <div
              className="font-semibold"
              style={{
                fontFamily: 'var(--font-display)',
                color: 'oklch(0.95 0.01 250)',
                fontSize: 'var(--fs-h2)',
                marginBottom: 'var(--space-3)',
              }}
            >
              {receiver.name}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
              <div className="flex items-center justify-between text-xs">
                <span style={{ color: 'oklch(0.6 0.02 250)' }}>Catches</span>
                <span className="font-semibold tabular-nums" style={{ color: 'oklch(0.95 0.01 250)' }}>
                  {receiver.catches}/{receiver.targets}
                </span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span style={{ color: 'oklch(0.6 0.02 250)' }}>Yards</span>
                <span className="font-semibold tabular-nums" style={{ color: 'oklch(0.95 0.01 250)' }}>
                  {receiver.yards}
                </span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span style={{ color: 'oklch(0.6 0.02 250)' }}>TDs</span>
                <span className="font-semibold tabular-nums" style={{ color: 'oklch(0.95 0.01 250)' }}>
                  {receiver.tds}
                </span>
              </div>
            </div>
          </div>
        ))}

        {/* Play Caller */}
        {!isPartial && (
          <div
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
                marginBottom: 'var(--space-2)',
              }}
            >
              {supportingData.playCaller.role}
            </div>
            <div
              className="font-semibold"
              style={{
                fontFamily: 'var(--font-display)',
                color: 'oklch(0.95 0.01 250)',
                fontSize: 'var(--fs-h2)',
                marginBottom: 'var(--space-2)',
              }}
            >
              {supportingData.playCaller.name}
            </div>
            <div className="text-xs" style={{ color: 'oklch(0.6 0.02 250)', marginBottom: 'var(--space-2)' }}>
              {supportingData.playCaller.scheme}
            </div>
            <p className="text-sm leading-relaxed" style={{ color: 'oklch(0.7 0.02 250)' }}>
              {supportingData.playCaller.narrative}
            </p>
          </div>
        )}

        {/* Defensive Coordinator */}
        {!isPartial && (
          <div
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
                marginBottom: 'var(--space-2)',
              }}
            >
              {supportingData.defCoordinator.role}
            </div>
            <div
              className="font-semibold"
              style={{
                fontFamily: 'var(--font-display)',
                color: 'oklch(0.95 0.01 250)',
                fontSize: 'var(--fs-h2)',
                marginBottom: 'var(--space-2)',
              }}
            >
              {supportingData.defCoordinator.name}
            </div>
            <div className="text-xs" style={{ color: 'oklch(0.6 0.02 250)', marginBottom: 'var(--space-2)' }}>
              {supportingData.defCoordinator.scheme}
            </div>
            <p className="text-sm leading-relaxed" style={{ color: 'oklch(0.7 0.02 250)' }}>
              {supportingData.defCoordinator.narrative}
            </p>
          </div>
        )}
      </div>

      <style>
        {`
          .cast-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: var(--space-4);
          }

          @container (min-width: 720px) {
            .cast-grid {
              grid-template-columns: repeat(2, 1fr);
            }
          }

          @container (min-width: 1200px) {
            .cast-grid {
              grid-template-columns: repeat(3, 1fr);
            }
          }
        `}
      </style>
    </div>
  );
}
