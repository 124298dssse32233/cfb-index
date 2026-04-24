// Peer Comparator — 5m tier
// Four peer players at the same rung with side-by-side stats and percentile bars
// User can swap any peer via search input (uses shadcn Input primitive)

import { useState } from 'react';
import { Input } from './ui/input';

type StateVariant = 'full' | 'empty' | 'loading' | 'partial' | 'error';

interface PlayerStat {
  label: string;
  value: number | string;
  percentile: number;
}

interface PeerPlayer {
  id: string;
  name: string;
  position: string;
  team: string;
  rung: number;
  stats: PlayerStat[];
}

export default function PeerComparator({ variant = 'full' }: { variant?: StateVariant }) {
  const [peers, setPeers] = useState<PeerPlayer[]>([
    {
      id: 'carr',
      name: 'CJ Carr',
      position: 'QB',
      team: 'Notre Dame',
      rung: 15,
      stats: [
        { label: 'EPA/dropback', value: 0.42, percentile: 91 },
        { label: 'CPOE', value: 8.2, percentile: 88 },
        { label: 'Completion %', value: '69.7%', percentile: 76 },
        { label: 'Yards', value: 4203, percentile: 92 },
        { label: 'TD', value: 38, percentile: 95 },
        { label: 'Int', value: 6, percentile: 94 },
      ],
    },
    {
      id: 'manning',
      name: 'Arch Manning',
      position: 'QB',
      team: 'Texas',
      rung: 15,
      stats: [
        { label: 'EPA/dropback', value: 0.39, percentile: 89 },
        { label: 'CPOE', value: 7.8, percentile: 85 },
        { label: 'Completion %', value: '71.2%', percentile: 82 },
        { label: 'Yards', value: 4012, percentile: 88 },
        { label: 'TD', value: 36, percentile: 92 },
        { label: 'Int', value: 8, percentile: 86 },
      ],
    },
    {
      id: 'beck',
      name: 'Carson Beck',
      position: 'QB',
      team: 'Georgia',
      rung: 15,
      stats: [
        { label: 'EPA/dropback', value: 0.38, percentile: 87 },
        { label: 'CPOE', value: 7.2, percentile: 82 },
        { label: 'Completion %', value: '68.4%', percentile: 74 },
        { label: 'Yards', value: 3892, percentile: 85 },
        { label: 'TD', value: 34, percentile: 88 },
        { label: 'Int', value: 7, percentile: 88 },
      ],
    },
    {
      id: 'gabriel',
      name: 'Dillon Gabriel',
      position: 'QB',
      team: 'Oregon',
      rung: 15,
      stats: [
        { label: 'EPA/dropback', value: 0.41, percentile: 90 },
        { label: 'CPOE', value: 8.5, percentile: 90 },
        { label: 'Completion %', value: '72.8%', percentile: 88 },
        { label: 'Yards', value: 4156, percentile: 90 },
        { label: 'TD', value: 37, percentile: 94 },
        { label: 'Int', value: 5, percentile: 96 },
      ],
    },
  ]);

  const [searchQuery, setSearchQuery] = useState('');
  const [replacingSlot, setReplacingSlot] = useState<number | null>(null);

  // Pool of available players for search
  const allPlayers: PeerPlayer[] = [
    ...peers,
    {
      id: 'ewers',
      name: 'Quinn Ewers',
      position: 'QB',
      team: 'Texas',
      rung: 12,
      stats: [
        { label: 'EPA/dropback', value: 0.35, percentile: 84 },
        { label: 'CPOE', value: 6.8, percentile: 78 },
        { label: 'Completion %', value: '67.2%', percentile: 71 },
        { label: 'Yards', value: 3654, percentile: 80 },
        { label: 'TD', value: 31, percentile: 84 },
        { label: 'Int', value: 9, percentile: 82 },
      ],
    },
    {
      id: 'dart',
      name: 'Jaxson Dart',
      position: 'QB',
      team: 'Ole Miss',
      rung: 11,
      stats: [
        { label: 'EPA/dropback', value: 0.33, percentile: 81 },
        { label: 'CPOE', value: 6.2, percentile: 74 },
        { label: 'Completion %', value: '66.8%', percentile: 69 },
        { label: 'Yards', value: 3542, percentile: 78 },
        { label: 'TD', value: 29, percentile: 80 },
        { label: 'Int', value: 10, percentile: 78 },
      ],
    },
  ];

  const filteredPlayers = searchQuery.trim()
    ? allPlayers.filter(
        (p) =>
          p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
          p.team.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : [];

  const handleReplacePlayer = (slotIndex: number, newPlayer: PeerPlayer) => {
    const newPeers = [...peers];
    newPeers[slotIndex] = newPlayer;
    setPeers(newPeers);
    setSearchQuery('');
    setReplacingSlot(null);
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
            PEER COMPARATOR
          </h2>
          <p className="text-sm" style={{ color: 'oklch(0.6 0.02 250)' }}>
            Side-by-side comparison · Awaiting peer data
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
            Peer comparison requires at least 4 players at the same rung tier. Check back when more R15 peers
            accumulate.
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
        <div className="peer-grid">
          {[1, 2, 3, 4].map((idx) => (
            <div
              key={idx}
              className="border"
              style={{
                background: 'oklch(0.20 0.01 250)',
                borderColor: 'oklch(0.28 0.01 250)',
                borderRadius: 'var(--radius-md)',
                height: '20rem',
              }}
            />
          ))}
        </div>
        <style>
          {`
            .peer-grid {
              display: grid;
              grid-template-columns: 1fr;
              gap: var(--space-4);
            }

            @container (min-width: 600px) {
              .peer-grid {
                grid-template-columns: repeat(2, 1fr);
              }
            }

            @container (min-width: 1200px) {
              .peer-grid {
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
            PEER COMPARATOR
          </h2>
          <p className="text-sm" style={{ color: 'oklch(0.6 0.02 250)' }}>
            Side-by-side comparison · Load failed
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
            Could not load peer comparison data. Try refreshing the page.
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

  // Partial state: only 2 peers available
  const isPartial = variant === 'partial';
  const displayPeers = isPartial ? peers.slice(0, 2) : peers;

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
          PEER COMPARATOR
        </h2>
        <p className="text-sm" style={{ color: 'oklch(0.6 0.02 250)' }}>
          {isPartial
            ? 'R15 Heisman tier · Partial (only 2 peers at this rung)'
            : 'R15 Heisman tier · Side-by-side stats · Tap any player to swap'}
        </p>
      </div>

      {/* Search bar (only show when replacing a slot) */}
      {replacingSlot !== null && (
        <div style={{ marginBottom: 'var(--space-6)' }}>
          <Input
            type="text"
            placeholder="Search by player name or team..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              minHeight: '44px',
            }}
          />
          {searchQuery.trim() && filteredPlayers.length > 0 && (
            <div
              className="border"
              style={{
                marginTop: 'var(--space-2)',
                background: 'oklch(0.20 0.01 250)',
                borderColor: 'oklch(0.28 0.01 250)',
                borderRadius: 'var(--radius-sm)',
                maxHeight: '16rem',
                overflowY: 'auto',
              }}
            >
              <div className="text-xs" style={{ padding: 'var(--space-2) var(--space-3)', color: 'oklch(0.6 0.02 250)' }}>
                {filteredPlayers.length} result{filteredPlayers.length !== 1 ? 's' : ''}
              </div>
              {filteredPlayers.map((player) => (
                <button
                  key={player.id}
                  type="button"
                  onClick={() => handleReplacePlayer(replacingSlot, player)}
                  style={{
                    width: '100%',
                    padding: 'var(--space-3)',
                    background: 'transparent',
                    border: 'none',
                    borderTop: '1px solid oklch(0.25 0.01 250)',
                    color: 'oklch(0.95 0.01 250)',
                    textAlign: 'left',
                    cursor: 'pointer',
                    transition: 'background var(--motion-state)',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = 'oklch(0.22 0.01 250)')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                >
                  <div className="font-semibold">{player.name}</div>
                  <div className="text-xs" style={{ color: 'oklch(0.6 0.02 250)' }}>
                    {player.position} · {player.team} · R{player.rung}
                  </div>
                </button>
              ))}
            </div>
          )}
          {searchQuery.trim() && filteredPlayers.length === 0 && (
            <div
              className="border text-sm"
              style={{
                marginTop: 'var(--space-2)',
                padding: 'var(--space-4)',
                background: 'oklch(0.20 0.01 250)',
                borderColor: 'oklch(0.28 0.01 250)',
                borderRadius: 'var(--radius-sm)',
                color: 'oklch(0.6 0.02 250)',
              }}
            >
              No matches for "{searchQuery}"
            </div>
          )}
        </div>
      )}

      {/* Peer cards grid */}
      <div className="peer-grid">
        {displayPeers.map((peer, idx) => (
          <div
            key={peer.id}
            className="border"
            style={{
              padding: 'var(--space-4)',
              background: 'oklch(0.20 0.01 250)',
              borderColor: replacingSlot === idx ? 'oklch(0.95 0.01 250)' : 'oklch(0.28 0.01 250)',
              borderRadius: 'var(--radius-md)',
              transition: 'border-color var(--motion-state)',
            }}
          >
            {/* Player header */}
            <div style={{ marginBottom: 'var(--space-4)' }}>
              <div className="flex items-center justify-between" style={{ marginBottom: 'var(--space-2)' }}>
                <h3
                  className="font-semibold"
                  style={{
                    fontFamily: 'var(--font-display)',
                    color: 'oklch(0.95 0.01 250)',
                    fontSize: 'var(--fs-h2)',
                  }}
                >
                  {peer.name}
                </h3>
                {!isPartial && (
                  <button
                    type="button"
                    onClick={() => setReplacingSlot(replacingSlot === idx ? null : idx)}
                    className="text-xs font-semibold"
                    style={{
                      padding: 'var(--space-1) var(--space-2)',
                      background: replacingSlot === idx ? 'oklch(0.3 0.01 250)' : 'transparent',
                      color: 'oklch(0.6 0.02 250)',
                      border: '1px solid oklch(0.28 0.01 250)',
                      borderRadius: 'var(--radius-sm)',
                      transition: 'background var(--motion-state)',
                    }}
                  >
                    {replacingSlot === idx ? 'Cancel' : 'Swap'}
                  </button>
                )}
              </div>
              <div className="text-xs" style={{ color: 'oklch(0.6 0.02 250)' }}>
                {peer.position} · {peer.team}
              </div>
            </div>

            {/* Stats */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
              {peer.stats.map((stat, statIdx) => (
                <div key={statIdx}>
                  <div className="flex items-baseline justify-between" style={{ marginBottom: 'var(--space-1)' }}>
                    <div className="text-xs" style={{ color: 'oklch(0.6 0.02 250)' }}>
                      {stat.label}
                    </div>
                    <div
                      className="font-semibold tabular-nums"
                      style={{
                        color: 'oklch(0.95 0.01 250)',
                        fontSize: 'var(--fs-body)',
                      }}
                    >
                      {stat.value}
                    </div>
                  </div>
                  <div
                    className="relative rounded-full"
                    style={{
                      height: 'var(--space-2)',
                      background: 'oklch(0.25 0.01 250)',
                    }}
                    role="meter"
                    aria-label={`${stat.label}: ${stat.percentile}th percentile`}
                    aria-valuenow={stat.percentile}
                    aria-valuemin={0}
                    aria-valuemax={100}
                  >
                    <div
                      className="absolute inset-y-0 left-0 rounded-full"
                      style={{
                        width: `${stat.percentile}%`,
                        background:
                          stat.percentile >= 90
                            ? 'var(--percentile-100)'
                            : stat.percentile >= 75
                              ? 'var(--percentile-90)'
                              : 'var(--percentile-75)',
                        transition: 'width var(--motion-data-entry)',
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      <style>
        {`
          .peer-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: var(--space-4);
          }

          @container (min-width: 600px) {
            .peer-grid {
              grid-template-columns: repeat(2, 1fr);
            }
          }

          @container (min-width: 1200px) {
            .peer-grid {
              grid-template-columns: repeat(4, 1fr);
            }
          }
        `}
      </style>
    </div>
  );
}
