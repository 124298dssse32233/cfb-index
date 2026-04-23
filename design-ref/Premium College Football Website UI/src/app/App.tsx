import { useState } from 'react';
import { Navigation } from './components/Navigation';
import { HomePage } from './components/HomePage';
import { TeamPage } from './components/TeamPage';
import { MatchupPage } from './components/MatchupPage';

export default function App() {
  const [currentPage, setCurrentPage] = useState<'home' | 'team' | 'matchup'>('home');

  return (
    <div className="min-h-screen" style={{ fontFamily: 'var(--font-sans)' }}>
      <Navigation currentPage={currentPage} onNavigate={setCurrentPage} />

      {currentPage === 'home' && (
        <HomePage
          onNavigateToTeam={() => setCurrentPage('team')}
          onNavigateToMatchup={() => setCurrentPage('matchup')}
        />
      )}

      {currentPage === 'team' && (
        <TeamPage onNavigateToMatchup={() => setCurrentPage('matchup')} />
      )}

      {currentPage === 'matchup' && <MatchupPage />}
    </div>
  );
}