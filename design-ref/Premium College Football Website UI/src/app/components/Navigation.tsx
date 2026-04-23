import { Search } from 'lucide-react';
import { useState } from 'react';

interface NavigationProps {
  currentPage: 'home' | 'team' | 'matchup';
  onNavigate: (page: 'home' | 'team' | 'matchup') => void;
}

export function Navigation({ currentPage, onNavigate }: NavigationProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <nav className="sticky top-0 z-50 bg-white/95 backdrop-blur-sm border-b border-[var(--border-strong)]">
      <div className="max-w-[1400px] mx-auto px-4 md:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 md:h-20">
          {/* Logo */}
          <button
            onClick={() => onNavigate('home')}
            className="flex items-center gap-3"
          >
            <div className="w-10 h-10 md:w-12 md:h-12 bg-[var(--primary)] rounded-lg flex items-center justify-center">
              <div className="text-white" style={{ fontFamily: 'var(--font-display)', fontSize: '24px', lineHeight: '1' }}>
                FI
              </div>
            </div>
            <div>
              <div style={{ fontFamily: 'var(--font-display)', fontSize: '20px', lineHeight: '1', letterSpacing: '0.02em' }}>
                FAN INTEL
              </div>
              <div className="text-[11px] text-[var(--muted-foreground)] tracking-wider hidden md:block">
                COLLEGE FOOTBALL
              </div>
            </div>
          </button>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-8">
            <button
              onClick={() => onNavigate('home')}
              className={`px-3 py-1.5 rounded-md transition-colors ${
                currentPage === 'home'
                  ? 'bg-[var(--accent)] text-[var(--accent-foreground)]'
                  : 'text-[var(--foreground)] hover:bg-[var(--secondary)]'
              }`}
            >
              Rankings
            </button>
            <button
              onClick={() => onNavigate('team')}
              className={`px-3 py-1.5 rounded-md transition-colors ${
                currentPage === 'team'
                  ? 'bg-[var(--accent)] text-[var(--accent-foreground)]'
                  : 'text-[var(--foreground)] hover:bg-[var(--secondary)]'
              }`}
            >
              Teams
            </button>
            <button
              onClick={() => onNavigate('matchup')}
              className={`px-3 py-1.5 rounded-md transition-colors ${
                currentPage === 'matchup'
                  ? 'bg-[var(--accent)] text-[var(--accent-foreground)]'
                  : 'text-[var(--foreground)] hover:bg-[var(--secondary)]'
              }`}
            >
              Matchups
            </button>
          </div>

          {/* Search & CTA */}
          <div className="flex items-center gap-3">
            <button className="p-2 hover:bg-[var(--secondary)] rounded-lg transition-colors">
              <Search className="w-5 h-5" />
            </button>
            <button className="hidden md:block px-4 py-2 bg-[var(--primary)] text-[var(--primary-foreground)] rounded-lg hover:opacity-90 transition-opacity">
              Compare Teams
            </button>
            <button
              className="md:hidden p-2"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            >
              <div className="w-5 h-5 flex flex-col justify-center gap-1">
                <div className="w-full h-0.5 bg-[var(--foreground)]"></div>
                <div className="w-full h-0.5 bg-[var(--foreground)]"></div>
                <div className="w-full h-0.5 bg-[var(--foreground)]"></div>
              </div>
            </button>
          </div>
        </div>

        {/* Mobile Menu */}
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-[var(--border)] py-4 space-y-2">
            <button
              onClick={() => {
                onNavigate('home');
                setMobileMenuOpen(false);
              }}
              className={`w-full text-left px-4 py-3 rounded-lg ${
                currentPage === 'home' ? 'bg-[var(--accent)] text-[var(--accent-foreground)]' : ''
              }`}
            >
              Rankings
            </button>
            <button
              onClick={() => {
                onNavigate('team');
                setMobileMenuOpen(false);
              }}
              className={`w-full text-left px-4 py-3 rounded-lg ${
                currentPage === 'team' ? 'bg-[var(--accent)] text-[var(--accent-foreground)]' : ''
              }`}
            >
              Teams
            </button>
            <button
              onClick={() => {
                onNavigate('matchup');
                setMobileMenuOpen(false);
              }}
              className={`w-full text-left px-4 py-3 rounded-lg ${
                currentPage === 'matchup' ? 'bg-[var(--accent)] text-[var(--accent-foreground)]' : ''
              }`}
            >
              Matchups
            </button>
            <button className="w-full px-4 py-3 bg-[var(--primary)] text-[var(--primary-foreground)] rounded-lg">
              Compare Teams
            </button>
          </div>
        )}
      </div>
    </nav>
  );
}
