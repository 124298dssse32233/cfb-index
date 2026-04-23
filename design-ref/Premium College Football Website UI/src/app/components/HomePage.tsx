import { TrendingUp, TrendingDown, Flame, Zap, Trophy, ArrowRight } from 'lucide-react';
import { useState } from 'react';
import { ConferenceFilter } from './ConferenceFilter';

interface HomePageProps {
  onNavigateToTeam: () => void;
  onNavigateToMatchup: () => void;
}

export function HomePage({ onNavigateToTeam, onNavigateToMatchup }: HomePageProps) {
  const [selectedConference, setSelectedConference] = useState('All');

  return (
    <div className="min-h-screen bg-[var(--background)]">
      {/* Hero Section */}
      <section className="relative overflow-hidden bg-gradient-to-br from-[var(--gradient-start)] via-[var(--gradient-end)] to-[var(--gradient-start)] text-white">
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-0 left-1/4 w-96 h-96 bg-[var(--gradient-accent)] rounded-full blur-3xl"></div>
          <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-blue-600 rounded-full blur-3xl"></div>
        </div>

        <div className="relative max-w-[1400px] mx-auto px-4 md:px-6 lg:px-8 py-12 md:py-20">
          <div className="max-w-4xl">
            <div className="inline-block px-3 py-1 bg-white/10 backdrop-blur-sm rounded-full text-sm mb-4 md:mb-6">
              Updated 3 hours ago • Week 12
            </div>
            <h1
              className="mb-4 md:mb-6"
              style={{
                fontFamily: 'var(--font-display)',
                fontSize: 'clamp(36px, 8vw, 72px)',
                lineHeight: '1',
                letterSpacing: '0.01em'
              }}
            >
              GEORGIA DROPS.<br />
              CHAOS RISES.
            </h1>
            <p className="text-lg md:text-xl text-white/80 mb-6 md:mb-8 max-w-2xl">
              The Bulldogs' collapse sent shockwaves through the top 10. Oregon's now the calmest fanbase in America.
              And Alabama fans? They're in full panic mode despite being 9-1.
            </p>
            <div className="flex flex-col sm:flex-row gap-4">
              <button
                onClick={onNavigateToMatchup}
                className="px-6 py-3 bg-white text-[var(--primary)] rounded-lg hover:bg-white/90 transition-colors inline-flex items-center justify-center gap-2"
              >
                See This Week's Chaos
                <ArrowRight className="w-5 h-5" />
              </button>
              <button className="px-6 py-3 bg-white/10 backdrop-blur-sm text-white rounded-lg hover:bg-white/20 transition-colors">
                Methodology
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Conference Filter */}
      <div className="border-b border-[var(--border)] bg-white sticky top-16 md:top-20 z-40">
        <div className="max-w-[1400px] mx-auto px-4 md:px-6 lg:px-8 py-4 md:py-6">
          <ConferenceFilter selected={selectedConference} onChange={setSelectedConference} />
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="max-w-[1400px] mx-auto px-4 md:px-6 lg:px-8 py-8 md:py-12">

        {/* Biggest Vibe Shifts */}
        <section className="mb-8 md:mb-12">
          <div className="flex items-center gap-3 mb-4 md:mb-6">
            <Zap className="w-6 h-6 md:w-7 md:h-7 text-[var(--warning)]" />
            <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(28px, 5vw, 42px)', lineHeight: '1', letterSpacing: '0.01em' }}>
              BIGGEST VIBE SHIFTS THIS WEEK
            </h2>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6">
            <VibeShiftCard
              team="Georgia Bulldogs"
              conference="SEC"
              rank={3}
              change={-2}
              shift={-42}
              color="var(--team-red)"
              onClick={onNavigateToTeam}
            />
            <VibeShiftCard
              team="Alabama Crimson Tide"
              conference="SEC"
              rank={5}
              change={0}
              shift={-38}
              color="var(--team-red)"
              onClick={onNavigateToTeam}
            />
            <VibeShiftCard
              team="Penn State"
              conference="Big Ten"
              rank={4}
              change={+1}
              shift={+35}
              color="var(--team-blue)"
              onClick={onNavigateToTeam}
            />
          </div>
        </section>

        {/* Two Column Layout */}
        <div className="grid lg:grid-cols-3 gap-8 md:gap-12 mb-8 md:mb-12">
          {/* Respect Gap Leaders */}
          <div className="lg:col-span-2">
            <div className="flex items-center gap-3 mb-4 md:mb-6">
              <Flame className="w-6 h-6 md:w-7 md:h-7 text-[var(--gradient-accent)]" />
              <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(28px, 5vw, 42px)', lineHeight: '1', letterSpacing: '0.01em' }}>
                RESPECT GAP LEADERS
              </h2>
            </div>
            <div className="bg-white rounded-xl border border-[var(--border)] overflow-hidden">
              <div className="p-4 md:p-6 space-y-4">
                <RespectGapRow
                  rank={1}
                  team="Oregon Ducks"
                  conference="Big Ten"
                  modelRank={1}
                  fanRank={8}
                  gap={7}
                  trend="up"
                  color="var(--team-green)"
                  onClick={onNavigateToTeam}
                />
                <RespectGapRow
                  rank={2}
                  team="Texas Longhorns"
                  conference="SEC"
                  modelRank={2}
                  fanRank={5}
                  gap={3}
                  trend="up"
                  color="var(--team-orange)"
                  onClick={onNavigateToTeam}
                />
                <RespectGapRow
                  rank={3}
                  team="Ohio State"
                  conference="Big Ten"
                  modelRank={6}
                  fanRank={2}
                  gap={-4}
                  trend="down"
                  color="var(--team-red)"
                  onClick={onNavigateToTeam}
                />
              </div>
            </div>
          </div>

          {/* Main Character of the Week */}
          <div>
            <div className="flex items-center gap-3 mb-4 md:mb-6">
              <Trophy className="w-6 h-6 md:w-7 md:h-7 text-[var(--team-gold)]" />
              <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(24px, 4vw, 32px)', lineHeight: '1', letterSpacing: '0.01em' }}>
                MAIN CHARACTER
              </h2>
            </div>
            <div className="bg-gradient-to-br from-[var(--team-orange)] to-[var(--team-red)] rounded-xl p-6 text-white relative overflow-hidden">
              <div className="absolute top-0 right-0 w-32 h-32 bg-white/10 rounded-full blur-2xl"></div>
              <div className="relative">
                <div className="text-sm opacity-80 mb-2">Week 12</div>
                <div style={{ fontFamily: 'var(--font-display)', fontSize: '32px', lineHeight: '1', letterSpacing: '0.01em' }} className="mb-3">
                  GEORGIA
                </div>
                <p className="text-sm opacity-90 mb-4">
                  From playoff lock to "wait, are we in trouble?" in one afternoon. The fanbase vibe crater of the season.
                </p>
                <button
                  onClick={onNavigateToTeam}
                  className="text-sm underline underline-offset-4 hover:no-underline"
                >
                  View team dossier →
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Cross-Division Shock Rankings */}
        <section className="mb-8 md:mb-12">
          <div className="mb-4 md:mb-6">
            <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(28px, 5vw, 42px)', lineHeight: '1', letterSpacing: '0.01em' }} className="mb-2">
              CROSS-DIVISION SHOCK RANKINGS
            </h2>
            <p className="text-[var(--muted-foreground)]">
              Conference perception vs actual model strength
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-4 md:gap-6">
            <ShockCard
              conference="ACC"
              perception="Weak"
              reality="Stronger than you think"
              highlight="Miami & Clemson both top-15 in model power"
              shockScore={7.8}
            />
            <ShockCard
              conference="Big 12"
              perception="Chaotic"
              reality="Actually pretty good"
              highlight="Four teams in model top-20 despite round-robin chaos"
              shockScore={6.4}
            />
          </div>
        </section>

        {/* Rival Heat Leaders */}
        <section>
          <div className="flex items-center gap-3 mb-4 md:mb-6">
            <Flame className="w-6 h-6 md:w-7 md:h-7 text-[var(--gradient-accent)]" />
            <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(28px, 5vw, 42px)', lineHeight: '1', letterSpacing: '0.01em' }}>
              RIVAL HEAT LEADERS
            </h2>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <RivalCard
              matchup="Ohio State vs Michigan"
              heat={9.8}
              tagline="The Game never disappoints"
              onClick={onNavigateToMatchup}
            />
            <RivalCard
              matchup="Alabama vs Auburn"
              heat={9.2}
              tagline="Iron Bowl intensity rising"
              onClick={onNavigateToMatchup}
            />
            <RivalCard
              matchup="USC vs Notre Dame"
              heat={8.7}
              tagline="Coast-to-coast hatred"
              onClick={onNavigateToMatchup}
            />
            <RivalCard
              matchup="Texas vs Oklahoma"
              heat={8.5}
              tagline="Red River grudge match"
              onClick={onNavigateToMatchup}
            />
          </div>
        </section>

      </div>

      {/* Footer */}
      <footer className="border-t border-[var(--border)] bg-white mt-12 md:mt-20">
        <div className="max-w-[1400px] mx-auto px-4 md:px-6 lg:px-8 py-8 md:py-12">
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
            <div>
              <div style={{ fontFamily: 'var(--font-display)', fontSize: '24px', lineHeight: '1', letterSpacing: '0.02em' }}>
                FAN INTEL
              </div>
              <p className="text-sm text-[var(--muted-foreground)] mt-2">
                Story-first power rankings for smart fans
              </p>
            </div>
            <div className="flex flex-wrap gap-6 text-sm">
              <button className="text-[var(--muted-foreground)] hover:text-[var(--foreground)]">Methodology</button>
              <button className="text-[var(--muted-foreground)] hover:text-[var(--foreground)]">About</button>
              <button className="text-[var(--muted-foreground)] hover:text-[var(--foreground)]">Sources</button>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

function VibeShiftCard({ team, conference, rank, change, shift, color, onClick }: any) {
  return (
    <button
      onClick={onClick}
      className="bg-white border border-[var(--border)] rounded-xl p-4 md:p-6 hover:shadow-lg transition-all text-left group"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color }}></div>
          <span className="text-xs text-[var(--muted-foreground)]">{conference}</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="text-sm">#{rank}</span>
          {change !== 0 && (
            <span className={change > 0 ? 'text-[var(--success)]' : 'text-[var(--destructive)]'}>
              {change > 0 ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
            </span>
          )}
        </div>
      </div>
      <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '24px', lineHeight: '1.2', letterSpacing: '0.01em' }} className="mb-3 group-hover:underline">
        {team}
      </h3>
      <div className="flex items-baseline gap-2">
        <span className="text-xs text-[var(--muted-foreground)]">Vibe Shift</span>
        <span className={`text-2xl ${shift < 0 ? 'text-[var(--destructive)]' : 'text-[var(--success)]'}`}>
          {shift > 0 ? '+' : ''}{shift}
        </span>
      </div>
    </button>
  );
}

function RespectGapRow({ rank, team, conference, modelRank, fanRank, gap, trend, color, onClick }: any) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-3 md:gap-4 p-3 md:p-4 rounded-lg hover:bg-[var(--secondary)] transition-colors w-full text-left group"
    >
      <div className="text-xl md:text-2xl text-[var(--muted-foreground)] min-w-[24px]">
        {rank}
      </div>
      <div className="w-1 h-12 rounded-full" style={{ backgroundColor: color }}></div>
      <div className="flex-1 min-w-0">
        <div style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(18px, 3vw, 22px)', lineHeight: '1.2' }} className="mb-1 group-hover:underline">
          {team}
        </div>
        <div className="text-xs text-[var(--muted-foreground)]">{conference}</div>
      </div>
      <div className="text-right">
        <div className="flex items-center gap-2 justify-end mb-1">
          <span className="text-xs text-[var(--muted-foreground)]">Model #{modelRank}</span>
          <span className="text-xs">→</span>
          <span className="text-xs text-[var(--muted-foreground)]">Fans #{fanRank}</span>
        </div>
        <div className={`text-lg ${gap > 0 ? 'text-[var(--success)]' : 'text-[var(--destructive)]'}`}>
          {gap > 0 ? '+' : ''}{gap} gap
        </div>
      </div>
    </button>
  );
}

function ShockCard({ conference, perception, reality, highlight, shockScore }: any) {
  return (
    <div className="bg-white border border-[var(--border)] rounded-xl p-4 md:p-6">
      <div className="flex items-start justify-between mb-4">
        <div style={{ fontFamily: 'var(--font-display)', fontSize: '28px', lineHeight: '1', letterSpacing: '0.01em' }}>
          {conference}
        </div>
        <div className="text-right">
          <div className="text-2xl">{shockScore}</div>
          <div className="text-xs text-[var(--muted-foreground)]">Shock Score</div>
        </div>
      </div>
      <div className="space-y-2 mb-4">
        <div className="flex items-center gap-2">
          <span className="text-xs text-[var(--muted-foreground)]">Perception:</span>
          <span className="text-sm">{perception}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-[var(--muted-foreground)]">Reality:</span>
          <span className="text-sm">{reality}</span>
        </div>
      </div>
      <p className="text-sm text-[var(--muted-foreground)]">{highlight}</p>
    </div>
  );
}

function RivalCard({ matchup, heat, tagline, onClick }: any) {
  return (
    <button
      onClick={onClick}
      className="bg-gradient-to-br from-[var(--team-red)] to-[var(--team-orange)] rounded-xl p-4 md:p-6 text-white hover:shadow-xl transition-all text-left group"
    >
      <div className="text-3xl mb-3">{heat}</div>
      <div style={{ fontFamily: 'var(--font-display)', fontSize: '18px', lineHeight: '1.2', letterSpacing: '0.01em' }} className="mb-2 group-hover:underline">
        {matchup}
      </div>
      <p className="text-sm opacity-90">{tagline}</p>
    </button>
  );
}
