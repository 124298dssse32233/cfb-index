import { TrendingUp, TrendingDown, Zap, AlertTriangle, Target, Users } from 'lucide-react';
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, BarChart, Bar } from 'recharts';

const quadrantData = [
  { x: 7.2, y: 8.1, team: 'Alabama', color: '#BA0C2F' },
  { x: 4.2, y: 6.5, team: 'Georgia', color: '#CC0000' },
  { x: 8.5, y: 9.2, team: 'Oregon', color: '#007030' },
  { x: 6.1, y: 5.8, team: 'Ohio State', color: '#BB0000' },
];

const marketMoodData = [
  { label: 'Model', value: 65, color: '#2563EB' },
  { label: 'Market', value: 58, color: '#9333EA' },
  { label: 'Fans', value: 42, color: '#DC2626' },
];

export function MatchupPage() {
  return (
    <div className="min-h-screen bg-[var(--background)]">
      {/* Hero Matchup Section */}
      <section className="relative overflow-hidden bg-gradient-to-br from-[var(--gradient-start)] via-[var(--gradient-end)] to-[var(--gradient-start)] text-white">
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-0 left-0 w-96 h-96 bg-[#BA0C2F] rounded-full blur-3xl"></div>
          <div className="absolute bottom-0 right-0 w-96 h-96 bg-[#CC0000] rounded-full blur-3xl"></div>
        </div>

        <div className="relative max-w-[1400px] mx-auto px-4 md:px-6 lg:px-8 py-8 md:py-16">
          <div className="text-center mb-8 md:mb-12">
            <div className="inline-block px-3 py-1 bg-white/10 backdrop-blur-sm rounded-full text-xs md:text-sm mb-4">
              Week 12 • Saturday, Nov 16 • 3:30 PM ET
            </div>
            <div style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(32px, 6vw, 56px)', lineHeight: '1.1', letterSpacing: '0.01em' }} className="mb-4">
              ARGUMENT THEATER
            </div>
            <p className="text-white/70 text-sm md:text-base max-w-2xl mx-auto">
              Where the model, the market, and the fans all disagree
            </p>
          </div>

          {/* Matchup Display */}
          <div className="grid md:grid-cols-3 gap-4 md:gap-6 items-center max-w-5xl mx-auto">
            {/* Team 1 */}
            <div className="bg-gradient-to-br from-[#BA0C2F] to-[#8B0A23] rounded-xl p-6 md:p-8 text-center">
              <div className="text-4xl md:text-6xl mb-3">🐘</div>
              <div style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(28px, 5vw, 42px)', lineHeight: '1', letterSpacing: '0.01em' }}>
                ALABAMA
              </div>
              <div className="text-white/70 text-sm md:text-base mb-4">Crimson Tide</div>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-white/70">Record</span>
                  <span>9-1</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-white/70">Rank</span>
                  <span>#5</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-white/70">Rating</span>
                  <span>88.7</span>
                </div>
              </div>
            </div>

            {/* VS */}
            <div className="text-center">
              <div className="w-16 h-16 md:w-20 md:h-20 mx-auto bg-white/10 backdrop-blur-sm rounded-full flex items-center justify-center border-2 border-white/30 mb-3">
                <span style={{ fontFamily: 'var(--font-display)', fontSize: '28px', lineHeight: '1' }}>VS</span>
              </div>
              <div className="text-sm text-white/70">Spread: Alabama -3.5</div>
            </div>

            {/* Team 2 */}
            <div className="bg-gradient-to-br from-[#CC0000] to-[#990000] rounded-xl p-6 md:p-8 text-center">
              <div className="text-4xl md:text-6xl mb-3">🐶</div>
              <div style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(28px, 5vw, 42px)', lineHeight: '1', letterSpacing: '0.01em' }}>
                GEORGIA
              </div>
              <div className="text-white/70 text-sm md:text-base mb-4">Bulldogs</div>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-white/70">Record</span>
                  <span>9-2</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-white/70">Rank</span>
                  <span>#3</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-white/70">Rating</span>
                  <span>91.2</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <div className="max-w-[1400px] mx-auto px-4 md:px-6 lg:px-8 py-8 md:py-12">
        {/* Which Fanbase is Calmer */}
        <section className="mb-8 md:mb-12">
          <div className="flex items-center gap-3 mb-4 md:mb-6">
            <Zap className="w-6 h-6 md:w-7 md:h-7 text-[var(--warning)]" />
            <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(28px, 5vw, 42px)', lineHeight: '1', letterSpacing: '0.01em' }}>
              WHICH FANBASE IS CALMER?
            </h2>
          </div>

          <div className="grid md:grid-cols-2 gap-6">
            <div className="bg-white border border-[var(--border)] rounded-xl p-6 md:p-8">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <div style={{ fontFamily: 'var(--font-display)', fontSize: '28px', lineHeight: '1', letterSpacing: '0.01em' }}>
                    ALABAMA
                  </div>
                  <div className="text-sm text-[var(--muted-foreground)]">Fan Confidence</div>
                </div>
                <div className="text-right">
                  <div className="text-4xl mb-1">7.2</div>
                  <div className="flex items-center gap-1 text-[var(--success)]">
                    <TrendingDown className="w-4 h-4" />
                    <span className="text-sm">-2.1</span>
                  </div>
                </div>
              </div>

              <div className="w-full bg-[var(--muted)] rounded-full h-4 mb-4">
                <div className="bg-[#BA0C2F] h-4 rounded-full" style={{ width: '72%' }}></div>
              </div>

              <p className="text-sm text-[var(--muted-foreground)]">
                Alabama fans are nervous despite the record. Too many close calls, and they know Georgia has their number historically.
              </p>
            </div>

            <div className="bg-white border border-[var(--border)] rounded-xl p-6 md:p-8">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <div style={{ fontFamily: 'var(--font-display)', fontSize: '28px', lineHeight: '1', letterSpacing: '0.01em' }}>
                    GEORGIA
                  </div>
                  <div className="text-sm text-[var(--muted-foreground)]">Fan Confidence</div>
                </div>
                <div className="text-right">
                  <div className="text-4xl mb-1">4.2</div>
                  <div className="flex items-center gap-1 text-[var(--destructive)]">
                    <TrendingDown className="w-4 h-4" />
                    <span className="text-sm">-3.8</span>
                  </div>
                </div>
              </div>

              <div className="w-full bg-[var(--muted)] rounded-full h-4 mb-4">
                <div className="bg-[#CC0000] h-4 rounded-full" style={{ width: '42%' }}></div>
              </div>

              <p className="text-sm text-[var(--muted-foreground)]">
                Georgia's fanbase is in full crisis mode. The bloom is off the rose, and every weakness is magnified. Panic level: HIGH.
              </p>
            </div>
          </div>

          <div className="mt-6 bg-gradient-to-r from-[#BA0C2F]/10 to-[#CC0000]/10 border border-[var(--border)] rounded-xl p-6 text-center">
            <div style={{ fontFamily: 'var(--font-display)', fontSize: '24px', lineHeight: '1', letterSpacing: '0.01em' }} className="mb-2">
              WINNER: ALABAMA FANS (+3.0 CALMER)
            </div>
            <p className="text-sm text-[var(--muted-foreground)]">
              But neither fanbase is sleeping easy
            </p>
          </div>
        </section>

        {/* Model vs Market vs Mood */}
        <section className="mb-8 md:mb-12">
          <div className="flex items-center gap-3 mb-4 md:mb-6">
            <Target className="w-6 h-6 md:w-7 md:h-7 text-[var(--team-purple)]" />
            <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(28px, 5vw, 42px)', lineHeight: '1', letterSpacing: '0.01em' }}>
              MODEL VS MARKET VS MOOD
            </h2>
          </div>

          <div className="bg-white border border-[var(--border)] rounded-xl p-6 md:p-8">
            <div className="mb-6">
              <h3 className="text-lg mb-2">Alabama Win Probability (%)</h3>
              <p className="text-sm text-[var(--muted-foreground)]">
                Three different perspectives on the same game
              </p>
            </div>

            <div className="h-64 mb-6">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={marketMoodData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#E8E8E8" />
                  <XAxis type="number" stroke="#6B6B6B" domain={[0, 100]} />
                  <YAxis type="category" dataKey="label" stroke="#6B6B6B" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'white',
                      border: '1px solid #E8E8E8',
                      borderRadius: '8px',
                    }}
                  />
                  <Bar dataKey="value" radius={[0, 8, 8, 0]}>
                    {marketMoodData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="grid sm:grid-cols-3 gap-4">
              <div className="p-4 bg-[#2563EB]/5 rounded-lg border border-[#2563EB]/20">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-3 h-3 rounded-full bg-[#2563EB]"></div>
                  <span className="text-sm">Model</span>
                </div>
                <div className="text-2xl mb-1">65%</div>
                <p className="text-xs text-[var(--muted-foreground)]">
                  Pure analytics favor Alabama on neutral field
                </p>
              </div>

              <div className="p-4 bg-[#9333EA]/5 rounded-lg border border-[#9333EA]/20">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-3 h-3 rounded-full bg-[#9333EA]"></div>
                  <span className="text-sm">Market</span>
                </div>
                <div className="text-2xl mb-1">58%</div>
                <p className="text-xs text-[var(--muted-foreground)]">
                  Vegas slightly less confident in Bama
                </p>
              </div>

              <div className="p-4 bg-[#DC2626]/5 rounded-lg border border-[#DC2626]/20">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-3 h-3 rounded-full bg-[#DC2626]"></div>
                  <span className="text-sm">Fan Mood</span>
                </div>
                <div className="text-2xl mb-1">42%</div>
                <p className="text-xs text-[var(--muted-foreground)]">
                  Georgia fans have given up hope
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* What Both Sides Fear */}
        <section className="mb-8 md:mb-12">
          <div className="flex items-center gap-3 mb-4 md:mb-6">
            <AlertTriangle className="w-6 h-6 md:w-7 md:h-7 text-[var(--warning)]" />
            <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(28px, 5vw, 42px)', lineHeight: '1', letterSpacing: '0.01em' }}>
              WHAT BOTH SIDES FEAR
            </h2>
          </div>

          <div className="grid md:grid-cols-2 gap-6">
            <FearCard
              team="Alabama"
              color="#BA0C2F"
              fears={[
                { fear: "Georgia's defensive line", intensity: 9.2 },
                { fear: "Playoff resume damage", intensity: 8.7 },
                { fear: "Turnover vulnerability", intensity: 7.8 },
              ]}
            />

            <FearCard
              team="Georgia"
              color="#CC0000"
              fears={[
                { fear: "Losing third straight", intensity: 9.8 },
                { fear: "Playoff hopes crushed", intensity: 9.5 },
                { fear: "Complete fanbase meltdown", intensity: 9.1 },
              ]}
            />
          </div>
        </section>

        {/* Mood Quadrant */}
        <section>
          <div className="flex items-center gap-3 mb-4 md:mb-6">
            <Users className="w-6 h-6 md:w-7 md:h-7 text-[var(--team-blue)]" />
            <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(28px, 5vw, 42px)', lineHeight: '1', letterSpacing: '0.01em' }}>
              FAN CONFIDENCE VS NATIONAL PERCEPTION
            </h2>
          </div>

          <div className="bg-white border border-[var(--border)] rounded-xl p-6 md:p-8">
            <div className="mb-6">
              <p className="text-sm text-[var(--muted-foreground)]">
                Where teams sit in the confidence/respect matrix
              </p>
            </div>

            <div className="h-80 md:h-96">
              <ResponsiveContainer width="100%" height="100%">
                <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E8E8E8" />
                  <XAxis
                    type="number"
                    dataKey="x"
                    name="Fan Confidence"
                    stroke="#6B6B6B"
                    domain={[0, 10]}
                    label={{ value: 'Fan Confidence', position: 'bottom', offset: 0 }}
                  />
                  <YAxis
                    type="number"
                    dataKey="y"
                    name="National Perception"
                    stroke="#6B6B6B"
                    domain={[0, 10]}
                    label={{ value: 'National Perception', angle: -90, position: 'left' }}
                  />
                  <Tooltip
                    cursor={{ strokeDasharray: '3 3' }}
                    contentStyle={{
                      backgroundColor: 'white',
                      border: '1px solid #E8E8E8',
                      borderRadius: '8px',
                    }}
                    formatter={(value: any) => value.toFixed(1)}
                  />
                  <Scatter data={quadrantData} fill="#8884d8">
                    {quadrantData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Scatter>
                </ScatterChart>
              </ResponsiveContainer>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-6 pt-6 border-t border-[var(--border)]">
              {quadrantData.map((team) => (
                <div key={team.team} className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: team.color }}></div>
                  <span className="text-sm">{team.team}</span>
                </div>
              ))}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

function FearCard({ team, color, fears }: any) {
  return (
    <div className="bg-white border border-[var(--border)] rounded-xl overflow-hidden">
      <div className="p-4 md:p-6" style={{ backgroundColor: `${color}15` }}>
        <div style={{ fontFamily: 'var(--font-display)', fontSize: '24px', lineHeight: '1', letterSpacing: '0.01em', color }}>
          {team}
        </div>
      </div>

      <div className="p-4 md:p-6 space-y-4">
        {fears.map((item: any, index: number) => (
          <div key={index}>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm">{item.fear}</span>
              <span className="text-sm text-[var(--muted-foreground)]">{item.intensity}/10</span>
            </div>
            <div className="w-full bg-[var(--muted)] rounded-full h-2">
              <div
                className="h-2 rounded-full"
                style={{
                  width: `${item.intensity * 10}%`,
                  backgroundColor: color
                }}
              ></div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
