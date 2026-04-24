// Bio / Recruiting / Transfer / Roster — deep tier
// Tabbed reference block with "—" fallback for missing data

import { useState } from 'react';

type StateVariant = 'full' | 'empty' | 'loading' | 'partial' | 'error';
type TabId = 'bio' | 'recruiting' | 'transfer' | 'roster';

interface BioData {
  hometown: string;
  highSchool: string;
  height: string;
  weight: string;
  class: string;
}

interface RecruitingData {
  composite: number;
  stars: number;
  rank: string;
  offers: string[];
}

interface TransferData {
  status: string;
  priorSchools: string[];
  portalDate: string;
}

interface RosterData {
  depthChart: string;
  year: string;
  eligibility: string;
  jerseyNumber: number;
}

export default function BioRecruitingTransferRoster({
  variant = 'full',
  initialTab,
  onTabChange,
}: {
  variant?: StateVariant;
  initialTab?: TabId;
  onTabChange?: (tab: TabId) => void;
}) {
  const [internalTab, setInternalTab] = useState<TabId>('bio');
  const activeTab = initialTab ?? internalTab;

  const handleTabChange = (tab: TabId) => {
    if (onTabChange) {
      onTabChange(tab);
    } else {
      setInternalTab(tab);
    }
  };

  const data = {
    bio: {
      hometown: 'Saline, MI',
      highSchool: 'Saline HS',
      height: '6-3',
      weight: 205,
      class: 'Sophomore',
    },
    recruiting: {
      composite: 0.9982,
      stars: 5,
      rank: '#2 QB, #8 Overall',
      offers: ['Notre Dame', 'Georgia', 'Alabama', 'Ohio State', 'Michigan', 'LSU', 'Clemson', 'USC'],
    },
    transfer: {
      status: 'Not in portal',
      priorSchools: [],
      portalDate: '—',
    },
    roster: {
      depthChart: 'QB1 (Starter)',
      year: 'Sophomore',
      eligibility: '3 years remaining',
      jerseyNumber: 7,
    },
  };

  const partialData = {
    ...data,
    recruiting: {
      composite: 0,
      stars: 0,
      rank: '—',
      offers: [],
    },
  };

  const tabLabels: Record<TabId, string> = {
    bio: 'Bio',
    recruiting: 'Recruiting',
    transfer: 'Transfer',
    roster: 'Roster',
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
            BIO & RECRUITING
          </h2>
          <p className="text-sm" style={{ color: 'oklch(0.6 0.02 250)' }}>
            Reference data · Awaiting player profile
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
            Player reference data is populated from official roster and recruiting services. Check back when the player
            profile is published.
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
        <div className="flex flex-wrap" style={{ gap: 'var(--space-2)', marginBottom: 'var(--space-6)' }}>
          {[1, 2, 3, 4].map((idx) => (
            <div
              key={idx}
              style={{
                height: '2.75rem',
                width: '5rem',
                background: 'oklch(0.25 0.01 250)',
                borderRadius: '999px',
              }}
            />
          ))}
        </div>
        <div
          className="border"
          style={{
            background: 'oklch(0.20 0.01 250)',
            borderColor: 'oklch(0.28 0.01 250)',
            borderRadius: 'var(--radius-md)',
            height: '12rem',
          }}
        />
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
            BIO & RECRUITING
          </h2>
          <p className="text-sm" style={{ color: 'oklch(0.6 0.02 250)' }}>
            Reference data · Load failed
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
            Could not load player reference data. Try refreshing the page.
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

  // Partial state: recruiting data missing
  const isPartial = variant === 'partial';
  const activeData = isPartial ? partialData : data;

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
          BIO & RECRUITING
        </h2>
        <p className="text-sm" style={{ color: 'oklch(0.6 0.02 250)' }}>
          {isPartial
            ? 'Reference data · Partial (recruiting data unavailable)'
            : 'Reference data · Hometown · HS · Measurables · Portal status'}
        </p>
      </div>

      {/* Tab bar */}
      <div className="flex flex-wrap" style={{ gap: 'var(--space-2)', marginBottom: 'var(--space-6)' }}>
        {(Object.keys(tabLabels) as TabId[]).map((tabId) => (
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
            onClick={() => handleTabChange(tabId)}
            aria-pressed={activeTab === tabId}
          >
            {tabLabels[tabId]}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div
        className="border"
        style={{
          padding: 'var(--space-6)',
          background: 'oklch(0.20 0.01 250)',
          borderColor: 'oklch(0.28 0.01 250)',
          borderRadius: 'var(--radius-md)',
        }}
      >
        {activeTab === 'bio' && (
          <div className="ref-grid">
            <div>
              <div
                className="font-medium tracking-wider uppercase"
                style={{
                  color: 'oklch(0.6 0.02 250)',
                  letterSpacing: '0.08em',
                  fontSize: 'var(--fs-meta)',
                  marginBottom: 'var(--space-1)',
                }}
              >
                HOMETOWN
              </div>
              <div className="text-sm" style={{ color: 'oklch(0.95 0.01 250)' }}>
                {activeData.bio.hometown}
              </div>
            </div>
            <div>
              <div
                className="font-medium tracking-wider uppercase"
                style={{
                  color: 'oklch(0.6 0.02 250)',
                  letterSpacing: '0.08em',
                  fontSize: 'var(--fs-meta)',
                  marginBottom: 'var(--space-1)',
                }}
              >
                HIGH SCHOOL
              </div>
              <div className="text-sm" style={{ color: 'oklch(0.95 0.01 250)' }}>
                {activeData.bio.highSchool}
              </div>
            </div>
            <div>
              <div
                className="font-medium tracking-wider uppercase"
                style={{
                  color: 'oklch(0.6 0.02 250)',
                  letterSpacing: '0.08em',
                  fontSize: 'var(--fs-meta)',
                  marginBottom: 'var(--space-1)',
                }}
              >
                HEIGHT
              </div>
              <div className="text-sm tabular-nums" style={{ color: 'oklch(0.95 0.01 250)' }}>
                {activeData.bio.height}
              </div>
            </div>
            <div>
              <div
                className="font-medium tracking-wider uppercase"
                style={{
                  color: 'oklch(0.6 0.02 250)',
                  letterSpacing: '0.08em',
                  fontSize: 'var(--fs-meta)',
                  marginBottom: 'var(--space-1)',
                }}
              >
                WEIGHT
              </div>
              <div className="text-sm tabular-nums" style={{ color: 'oklch(0.95 0.01 250)' }}>
                {activeData.bio.weight} lbs
              </div>
            </div>
            <div>
              <div
                className="font-medium tracking-wider uppercase"
                style={{
                  color: 'oklch(0.6 0.02 250)',
                  letterSpacing: '0.08em',
                  fontSize: 'var(--fs-meta)',
                  marginBottom: 'var(--space-1)',
                }}
              >
                CLASS
              </div>
              <div className="text-sm" style={{ color: 'oklch(0.95 0.01 250)' }}>
                {activeData.bio.class}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'recruiting' && (
          <div className="ref-grid">
            <div>
              <div
                className="font-medium tracking-wider uppercase"
                style={{
                  color: 'oklch(0.6 0.02 250)',
                  letterSpacing: '0.08em',
                  fontSize: 'var(--fs-meta)',
                  marginBottom: 'var(--space-1)',
                }}
              >
                247 COMPOSITE
              </div>
              <div className="text-sm tabular-nums" style={{ color: 'oklch(0.95 0.01 250)' }}>
                {activeData.recruiting.composite > 0 ? activeData.recruiting.composite.toFixed(4) : '—'}
              </div>
            </div>
            <div>
              <div
                className="font-medium tracking-wider uppercase"
                style={{
                  color: 'oklch(0.6 0.02 250)',
                  letterSpacing: '0.08em',
                  fontSize: 'var(--fs-meta)',
                  marginBottom: 'var(--space-1)',
                }}
              >
                STAR RATING
              </div>
              <div className="text-sm" style={{ color: 'oklch(0.95 0.01 250)' }}>
                {activeData.recruiting.stars > 0 ? `${'★'.repeat(activeData.recruiting.stars)}` : '—'}
              </div>
            </div>
            <div>
              <div
                className="font-medium tracking-wider uppercase"
                style={{
                  color: 'oklch(0.6 0.02 250)',
                  letterSpacing: '0.08em',
                  fontSize: 'var(--fs-meta)',
                  marginBottom: 'var(--space-1)',
                }}
              >
                RANK
              </div>
              <div className="text-sm" style={{ color: 'oklch(0.95 0.01 250)' }}>
                {activeData.recruiting.rank}
              </div>
            </div>
            <div style={{ gridColumn: '1 / -1' }}>
              <div
                className="font-medium tracking-wider uppercase"
                style={{
                  color: 'oklch(0.6 0.02 250)',
                  letterSpacing: '0.08em',
                  fontSize: 'var(--fs-meta)',
                  marginBottom: 'var(--space-2)',
                }}
              >
                OFFERS ({activeData.recruiting.offers.length > 0 ? activeData.recruiting.offers.length : 0})
              </div>
              {activeData.recruiting.offers.length > 0 ? (
                <div className="flex flex-wrap" style={{ gap: 'var(--space-2)' }}>
                  {activeData.recruiting.offers.map((school, idx) => (
                    <div
                      key={idx}
                      className="text-xs"
                      style={{
                        padding: 'var(--space-1) var(--space-3)',
                        background: 'oklch(0.25 0.01 250)',
                        color: 'oklch(0.95 0.01 250)',
                        borderRadius: '999px',
                      }}
                    >
                      {school}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-sm" style={{ color: 'oklch(0.6 0.02 250)' }}>
                  Recruiting data unavailable for this player
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'transfer' && (
          <div className="ref-grid">
            <div>
              <div
                className="font-medium tracking-wider uppercase"
                style={{
                  color: 'oklch(0.6 0.02 250)',
                  letterSpacing: '0.08em',
                  fontSize: 'var(--fs-meta)',
                  marginBottom: 'var(--space-1)',
                }}
              >
                PORTAL STATUS
              </div>
              <div className="text-sm" style={{ color: 'oklch(0.95 0.01 250)' }}>
                {activeData.transfer.status}
              </div>
            </div>
            <div>
              <div
                className="font-medium tracking-wider uppercase"
                style={{
                  color: 'oklch(0.6 0.02 250)',
                  letterSpacing: '0.08em',
                  fontSize: 'var(--fs-meta)',
                  marginBottom: 'var(--space-1)',
                }}
              >
                PORTAL DATE
              </div>
              <div className="text-sm" style={{ color: 'oklch(0.95 0.01 250)' }}>
                {activeData.transfer.portalDate}
              </div>
            </div>
            <div style={{ gridColumn: '1 / -1' }}>
              <div
                className="font-medium tracking-wider uppercase"
                style={{
                  color: 'oklch(0.6 0.02 250)',
                  letterSpacing: '0.08em',
                  fontSize: 'var(--fs-meta)',
                  marginBottom: 'var(--space-1)',
                }}
              >
                PRIOR SCHOOLS
              </div>
              <div className="text-sm" style={{ color: 'oklch(0.95 0.01 250)' }}>
                {activeData.transfer.priorSchools.length > 0 ? activeData.transfer.priorSchools.join(', ') : '—'}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'roster' && (
          <div className="ref-grid">
            <div>
              <div
                className="font-medium tracking-wider uppercase"
                style={{
                  color: 'oklch(0.6 0.02 250)',
                  letterSpacing: '0.08em',
                  fontSize: 'var(--fs-meta)',
                  marginBottom: 'var(--space-1)',
                }}
              >
                DEPTH CHART
              </div>
              <div className="text-sm" style={{ color: 'oklch(0.95 0.01 250)' }}>
                {activeData.roster.depthChart}
              </div>
            </div>
            <div>
              <div
                className="font-medium tracking-wider uppercase"
                style={{
                  color: 'oklch(0.6 0.02 250)',
                  letterSpacing: '0.08em',
                  fontSize: 'var(--fs-meta)',
                  marginBottom: 'var(--space-1)',
                }}
              >
                YEAR
              </div>
              <div className="text-sm" style={{ color: 'oklch(0.95 0.01 250)' }}>
                {activeData.roster.year}
              </div>
            </div>
            <div>
              <div
                className="font-medium tracking-wider uppercase"
                style={{
                  color: 'oklch(0.6 0.02 250)',
                  letterSpacing: '0.08em',
                  fontSize: 'var(--fs-meta)',
                  marginBottom: 'var(--space-1)',
                }}
              >
                ELIGIBILITY
              </div>
              <div className="text-sm" style={{ color: 'oklch(0.95 0.01 250)' }}>
                {activeData.roster.eligibility}
              </div>
            </div>
            <div>
              <div
                className="font-medium tracking-wider uppercase"
                style={{
                  color: 'oklch(0.6 0.02 250)',
                  letterSpacing: '0.08em',
                  fontSize: 'var(--fs-meta)',
                  marginBottom: 'var(--space-1)',
                }}
              >
                JERSEY #
              </div>
              <div className="text-sm tabular-nums" style={{ color: 'oklch(0.95 0.01 250)' }}>
                {activeData.roster.jerseyNumber}
              </div>
            </div>
          </div>
        )}
      </div>

      <style>
        {`
          .ref-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: var(--space-4);
          }

          @container (min-width: 600px) {
            .ref-grid {
              grid-template-columns: repeat(2, 1fr);
            }
          }

          @container (min-width: 900px) {
            .ref-grid {
              grid-template-columns: repeat(3, 1fr);
            }
          }
        `}
      </style>
    </div>
  );
}
