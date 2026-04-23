import { TrendingUp, TrendingDown, Heart, Users, Flame, ArrowRight, Trophy, Zap } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from 'recharts';

interface TeamPageProps {
  onNavigateToMatchup: () => void;
}

const ratingHistory = [
  { week: 'W1', rating: 85, fanMood: 7.2, event: 'Season Start' },
  { week: 'W2', rating: 87, fanMood: 7.8, event: null },
  { week: 'W3', rating: 88, fanMood: 8.1, event: null },
  { week: 'W4', rating: 90, fanMood: 8.5, event: 'Big Win' },
  { week: 'W5', rating: 91, fanMood: 8.7, event: null },
  { week: 'W6', rating: 89, fanMood: 7.9, event: null },
  { week: 'W7', rating: 86, fanMood: 6.8, event: 'Close Call' },
  { week: 'W8', rating: 84, fanMood: 6.2, event: null },
  { week: 'W9', rating: 82, fanMood: 5.5, event: 'Loss' },
  { week: 'W10', rating: 80, fanMood: 4.8, event: null },
  { week: 'W11', rating: 78, fanMood: 4.2, event: null },
];

export function TeamPage({ onNavigateToMatchup }: TeamPageProps) {
  return (
    <div className="min-h-screen bg-[var(--background)]">
      {/* Hero Section */}
      <section className="relative overflow-hidden bg-gradient-to-br from-[#BA0C2F] via-[#8B0A23] to-[#5C0617] text-white">
        <div className="absolute inset-0 opacity-20">
          <div className="absolute top-1/4 right-1/4 w-96 h-96 bg-white rounded-full blur-3xl"></div>
        </div>

        <div className="relative max-w-[1400px] mx-auto px-4 md:px-6 lg:px-8 py-8 md:py-16">
          <div className="flex flex-col lg:flex-row gap-8 md:gap-12 items-start">
            {/* Team Identity */}
            <div className="flex-1">
              <div className="inline-block px-3 py-1 bg-white/10 backdrop-blur-sm rounded-full text-xs md:text-sm mb-4">
                SEC • Updated 2 hours ago
              </div>

              <div className="flex items-center gap-4 md:gap-6 mb-4 md:mb-6">
                <div className="w-16 h-16 md:w-24 md:h-24 bg-white/10 backdrop-blur-sm rounded-2xl flex items-center justify-center border border-white/20">
                  <div className="text-3xl md:text-5xl">🐶</div>
                </div>
                <div>
                  <div style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(36px, 8vw, 64px)', lineHeight: '1', letterSpacing: '0.01em' }}>
                    GEORGIA
                  </div>
                  <div className="text-white/80 text-lg md:text-xl">Bulldogs</div>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-4 md:gap-6 mb-6 md:mb-8">
                <div>
                  <div className="text-4xl md:text-5xl mb-1">9-2</div>
                  <div className="text-sm text-white/70">Record</div>
                </div>
                <div className="w-px h-12 bg-white/20"></div>
                <div>
                  <div className="text-4xl md:text-5xl mb-1">#3</div>
                  <div className="text-sm text-white/70">National Rank</div>
                </div>
                <div className="w-px h-12 bg-white/20"></div>
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-4xl md:text-5xl">91.2</span>
                    <TrendingDown className="w-6 h-6 md:w-8 md:h-8 text-red-300" />
                  </div>
                  <div className="text-sm text-white/70">Power Rating</div>
                </div>
              </div>

              <p className="text-base md:text-lg text-white/90 mb-6 md:mb-8 max-w-2xl">
                The Bulldogs' playoff path just got complicated. After dominating the first half of the season,
                back-to-back losses have fans questioning everything. The talent is still elite, but the confidence? That's evaporating fast.
              </p>

              <div className="flex flex-col sm:flex-row gap-3">
                <button
                  onClick={onNavigateToMatchup}
                  className="px-6 py-3 bg-white text-[#BA0C2F] rounded-lg hover:bg-white/90 transition-colors inline-flex items-center justify-center gap-2"
                >
                  Compare vs Rival
                  <ArrowRight className="w-5 h-5" />
                </button>
                <button className="px-6 py-3 bg-white/10 backdrop-blur-sm text-white rounded-lg hover:bg-white/20 transition-colors">
                  View Full Schedule
                </button>
              </div>
            </div>

            {/* Quick Stats */}
            <div className="lg:w-80">
              <div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-xl p-4 md:p-6">
                <h3 className="text-sm uppercase tracking-wider mb-4 text-white/70">Season Snapshot</h3>
                <div className="space-y-4">
                  <StatRow label="AP Poll" value="#3" change="-2" />
                  <StatRow label="Playoff Odds" value="78%" change="-22%" />
                  <StatRow label="SOS Rank" value="#12" change="+3" />
                  <StatRow label="Off. Efficiency" value="#8" change="-1" />
                  <StatRow label="Def. Efficiency" value="#2" change="0" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <div className="max-w-[1400px] mx-auto px-4 md:px-6 lg:px-8 py-8 md:py-12">
        {/* Team Mood Card - Flagship Feature */}
        <section className="mb-8 md:mb-12">
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(28px, 5vw, 42px)', lineHeight: '1', letterSpacing: '0.01em' }} className="mb-4 md:mb-6">
            TEAM MOOD DASHBOARD
          </h2>

          <div className="grid md:grid-cols-2 lg:grid-cols-5 gap-4">
            <MoodMetricCard
              icon={<Heart className="w-5 h-5 md:w-6 md:h-6" />}
              label="Fan Pulse"
              value={4.2}
              max={10}
              change={-3.8}
              color="var(--team-red)"
              description="Fanbase confidence at season low"
            />
            <MoodMetricCard
              icon={<Users className="w-5 h-5 md:w-6 md:h-6" />}
              label="National Mood"
              value={6.5}
              max={10}
              change={-1.2}
              color="var(--team-blue)"
              description="Still respected nationally"
            />
            <MoodMetricCard
              icon={<Flame className="w-5 h-5 md:w-6 md:h-6" />}
              label="Respect Gap"
              value={-2.3}
              max={10}
              change={-2.8}
              color="var(--team-orange)"
              description="Fans more pessimistic than model"
            />
            <MoodMetricCard
              icon={<Zap className="w-5 h-5 md:w-6 md:h-6" />}
              label="Rival Heat"
              value={9.1}
              max={10}
              change={+0.5}
              color="var(--team-purple)"
              description="Florida & Tennessee tension rising"
            />
            <MoodMetricCard
              icon={<Trophy className="w-5 h-5 md:w-6 md:h-6" />}
              label="Belief Shift"
              value={-42}
              max={100}
              change={-42}
              color="var(--destructive)"
              description="Biggest confidence drop in SEC"
            />
          </div>
        </section>

        {/* Season Journey Chart */}
        <section className="mb-8 md:mb-12">
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(28px, 5vw, 42px)', lineHeight: '1', letterSpacing: '0.01em' }} className="mb-4 md:mb-6">
            SEASON JOURNEY
          </h2>

          <div className="bg-white border border-[var(--border)] rounded-xl p-4 md:p-8">
            <div className="mb-6">
              <h3 className="text-lg mb-1">Power Rating & Fan Mood Over Time</h3>
              <p className="text-sm text-[var(--muted-foreground)]">
                The recent divergence tells the story
              </p>
            </div>

            <div className="h-64 md:h-80">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={ratingHistory}>
                  <defs>
                    <linearGradient id="colorRating" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#2563EB" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#2563EB" stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="colorMood" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#DC2626" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#DC2626" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E8E8E8" />
                  <XAxis dataKey="week" stroke="#6B6B6B" />
                  <YAxis stroke="#6B6B6B" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'white',
                      border: '1px solid #E8E8E8',
                      borderRadius: '8px',
                      boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="rating"
                    stroke="#2563EB"
                    strokeWidth={3}
                    fillOpacity={1}
                    fill="url(#colorRating)"
                    name="Power Rating"
                  />
                  <Area
                    type="monotone"
                    dataKey="fanMood"
                    stroke="#DC2626"
                    strokeWidth={3}
                    fillOpacity={1}
                    fill="url(#colorMood)"
                    name="Fan Mood"
                    yAxisId={0}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            <div className="flex flex-wrap gap-6 mt-6 pt-6 border-t border-[var(--border)]">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-[#2563EB]"></div>
                <span className="text-sm">Power Rating</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-[#DC2626]"></div>
                <span className="text-sm">Fan Mood</span>
              </div>
            </div>
          </div>
        </section>

        {/* Two Column Layout */}
        <div className="grid lg:grid-cols-3 gap-8 md:gap-12">
          {/* Top Storylines */}
          <div className="lg:col-span-2">
            <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(28px, 5vw, 42px)', lineHeight: '1', letterSpacing: '0.01em' }} className="mb-4 md:mb-6">
              TOP STORYLINES
            </h2>

            <div className="space-y-4">
              <StorylineCard
                title="The Collapse is Real"
                excerpt="From undefeated juggernaut to barely hanging on. Two losses in three weeks have exposed vulnerabilities on both sides of the ball."
                sentiment="negative"
                engagement={8.9}
              />
              <StorylineCard
                title="Playoff Picture Murky"
                excerpt="Georgia's margin for error is gone. They need help from other teams and must win out convincingly to secure a spot."
                sentiment="neutral"
                engagement={7.6}
              />
              <StorylineCard
                title="Recruiting Class Still Elite"
                excerpt="Despite on-field struggles, Georgia's 2024 recruiting class remains #1 nationally. The future is still bright."
                sentiment="positive"
                engagement={6.2}
              />
            </div>
          </div>

          {/* Key Comparisons */}
          <div>
            <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(24px, 4vw, 32px)', lineHeight: '1', letterSpacing: '0.01em' }} className="mb-4 md:mb-6">
              KEY COMPARISONS
            </h2>

            <div className="space-y-3">
              <ComparisonCard
                team1="Georgia"
                team2="Alabama"
                metric="Fan Confidence"
                winner="Alabama"
                gap={"+2.1"} onCompare={onNavigateToMatchup}
              />
              <ComparisonCard
                team1="Georgia"
                team2="Texas"
                metric="Model Power"
                winner="Georgia"
                gap={"+4.8"}
                onCompare={onNavigateToMatchup}
              />
              <ComparisonCard
                team1="Georgia"
                team2="Florida St"
                metric="Recruiting"
                winner="Georgia"
                gap={"+12.5"}
                onCompare={onNavigateToMatchup}
              />
            </div>

            <button
              onClick={onNavigateToMatchup}
              className="w-full mt-6 px-6 py-3 bg-[var(--primary)] text-[var(--primary-foreground)] rounded-lg hover:opacity-90 transition-opacity inline-flex items-center justify-center gap-2"
            >
              Simulate Any Matchup
              <ArrowRight className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatRow({ label, value, change }: any) {
  const isNegative = change?.startsWith('-');
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-white/70">{label}</span>
      <div className="flex items-center gap-2">
        <span className="text-lg">{value}</span>
        {change && (
          <span className={`text-xs ${isNegative ? 'text-red-300' : 'text-green-300'}`}>
            {change}
          </span>
        )}
      </div>
    </div>
  );
}

function MoodMetricCard({ icon, label, value, max, change, color, description }: any) {
  const percentage = Math.abs(value) / max * 100;
  const isNegative = change < 0;

  return (
    <div className="bg-white border border-[var(--border)] rounded-xl p-4 md:p-6">
      <div className="flex items-center gap-3 mb-4">
        <div className="p-2 rounded-lg" style={{ backgroundColor: `${color}20`, color }}>
          {icon}
        </div>
        <div className="text-sm text-[var(--muted-foreground)]">{label}</div>
      </div>

      <div className="mb-3">
        <div className="text-3xl md:text-4xl mb-1">{value.toFixed(1)}</div>
        <div className="flex items-center gap-1">
          <span className={`text-sm ${isNegative ? 'text-[var(--destructive)]' : 'text-[var(--success)]'}`}>
            {change > 0 ? '+' : ''}{change.toFixed(1)}
          </span>
          {isNegative ? (
            <TrendingDown className="w-4 h-4 text-[var(--destructive)]" />
          ) : (
            <TrendingUp className="w-4 h-4 text-[var(--success)]" />
          )}
        </div>
      </div>

      <div className="w-full bg-[var(--muted)] rounded-full h-2 mb-3">
        <div
          className="h-2 rounded-full transition-all"
          style={{ width: `${percentage}%`, backgroundColor: color }}
        ></div>
      </div>

      <p className="text-xs text-[var(--muted-foreground)]">{description}</p>
    </div>
  );
}

function StorylineCard({ title, excerpt, sentiment, engagement }: any) {
  const sentimentColors = {
    positive: 'var(--success)',
    negative: 'var(--destructive)',
    neutral: 'var(--muted-foreground)'
  };

  return (
    <div className="bg-white border border-[var(--border)] rounded-xl p-4 md:p-6 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-3">
        <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '20px', lineHeight: '1.2', letterSpacing: '0.01em' }}>
          {title}
        </h3>
        <div className="flex items-center gap-1 text-sm text-[var(--muted-foreground)]">
          <Heart className="w-4 h-4" />
          <span>{engagement}</span>
        </div>
      </div>
      <p className="text-sm text-[var(--muted-foreground)] mb-3">{excerpt}</p>
      <div className="flex items-center gap-2">
        <div
          className="w-2 h-2 rounded-full"
          style={{ backgroundColor: sentimentColors[sentiment as keyof typeof sentimentColors] }}
        ></div>
        <span className="text-xs capitalize text-[var(--muted-foreground)]">{sentiment} sentiment</span>
      </div>
    </div>
  );
}

function ComparisonCard({ team1, team2, metric, winner, gap, onCompare }: any) {
  return (
    <button
      onClick={onCompare}
      className="w-full bg-white border border-[var(--border)] rounded-lg p-4 hover:shadow-md transition-shadow text-left group"
    >
      <div className="text-xs text-[var(--muted-foreground)] mb-2">{metric}</div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-sm group-hover:underline">{team1}</span>
        <span className="text-xs text-[var(--muted-foreground)]">vs</span>
        <span className="text-sm group-hover:underline">{team2}</span>
      </div>
      <div className="flex items-center justify-between">
        <span className="text-xs text-[var(--muted-foreground)]">{winner} leads</span>
        <span className="text-sm">{gap}</span>
      </div>
    </button>
  );
}
