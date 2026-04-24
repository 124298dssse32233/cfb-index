// Player Page — Full page flow
// Assembles all 10 modules in locked order, renders at 1440/768/375 via container queries
// Sub-route URL states: ?standing=R15 ?splits=down-distance ?bio=recruiting ?room=rivals ?savant=g5 ?peers=search:X

import { useState, useEffect, useRef } from 'react';
import { Subnav, SubnavAnchor } from '../components/ui/subnav';
import HeroFingerprint from '../components/HeroFingerprint';
import PlayerStanding from '../components/PlayerStanding';
import TheRoomOnPlayer from '../components/TheRoomOnPlayer';
import SignatureStory from '../components/SignatureStory';
import CurrentSeasonProduction from '../components/CurrentSeasonProduction';
import AdvancedSavantCard from '../components/AdvancedSavantCard';
import Splits from '../components/Splits';
import PeerComparator from '../components/PeerComparator';
import SupportingCast from '../components/SupportingCast';
import BioRecruitingTransferRoster from '../components/BioRecruitingTransferRoster';

// URL state management hook
function useURLState() {
  const [searchParams, setSearchParams] = useState(() => {
    if (typeof window === 'undefined') return new URLSearchParams();
    return new URLSearchParams(window.location.search);
  });

  const updateParam = (key: string, value: string | null) => {
    const newParams = new URLSearchParams(searchParams);
    if (value === null) {
      newParams.delete(key);
    } else {
      newParams.set(key, value);
    }
    setSearchParams(newParams);
    if (typeof window !== 'undefined') {
      const newUrl = `${window.location.pathname}${newParams.toString() ? '?' + newParams.toString() : ''}`;
      window.history.replaceState({}, '', newUrl);
    }
  };

  return { searchParams, updateParam };
}

type PageVariant = 'full' | 'loading' | 'partial' | 'error';

interface PlayerPageProps {
  variant?: PageVariant;
  playerId?: string;
}

export default function PlayerPage({ variant = 'full', playerId = 'carr-cj' }: PlayerPageProps) {
  // Error state
  if (variant === 'error') {
    return (
      <div className="dark min-h-screen bg-background">
        <div className="page-wrapper">
          <div className="page-content">
            <div
              className="border"
              style={{
                background: 'oklch(0.18 0.01 250)',
                borderColor: 'oklch(0.25 0.01 250)',
                borderRadius: 'var(--radius-lg)',
                padding: 'var(--space-12)',
                marginTop: 'var(--space-16)',
              }}
            >
              <h1
                className="leading-none tracking-tight uppercase"
                style={{
                  fontFamily: 'var(--font-display)',
                  color: 'oklch(0.95 0.01 250)',
                  fontWeight: 700,
                  fontSize: 'var(--fs-display)',
                  marginBottom: 'var(--space-4)',
                }}
              >
                PLAYER NOT FOUND
              </h1>
              <p
                className="leading-relaxed"
                style={{
                  color: 'oklch(0.7 0.02 250)',
                  fontSize: 'var(--fs-body)',
                  marginBottom: 'var(--space-6)',
                }}
              >
                No player profile exists for ID "{playerId}". Check the URL or search for another player.
              </p>
              <button
                type="button"
                className="text-sm font-semibold"
                style={{
                  padding: 'var(--space-3) var(--space-4)',
                  background: 'oklch(0.3 0.01 250)',
                  color: 'oklch(0.95 0.01 250)',
                  border: 'none',
                  borderRadius: 'var(--radius-sm)',
                  transition: 'background var(--motion-state)',
                  minHeight: '44px',
                }}
              >
                Return to search
              </button>
            </div>
          </div>
        </div>
        <style>
          {`
            .page-wrapper {
              container-type: inline-size;
            }

            .page-content {
              max-width: 1440px;
              margin: 0 auto;
              padding: var(--space-12);
            }

            @container (max-width: 768px) {
              .page-content {
                padding: var(--space-8);
              }
            }

            @container (max-width: 375px) {
              .page-content {
                padding: var(--space-4);
              }
            }
          `}
        </style>
      </div>
    );
  }

  // Loading state
  if (variant === 'loading') {
    const loadingAnchors: SubnavAnchor[] = [
      { id: 'hero', label: 'Hero', href: '#hero' },
      { id: 'standing', label: 'Standing', href: '#standing' },
      { id: 'room', label: 'Room', href: '#room' },
      { id: 'story', label: 'Story', href: '#story' },
      { id: 'production', label: 'Production', href: '#production' },
      { id: 'savant', label: 'Savant', href: '#savant' },
      { id: 'splits', label: 'Splits', href: '#splits' },
      { id: 'peers', label: 'Peers', href: '#peers' },
      { id: 'cast', label: 'Cast', href: '#cast' },
      { id: 'bio', label: 'Bio', href: '#bio' },
    ];

    return (
      <div className="dark min-h-screen bg-background">
        <Subnav
          playerName="Loading..."
          playerTeam="—"
          playerPosition="—"
          anchors={loadingAnchors}
          isSticky={false}
          isLoading={true}
        />
        <div className="page-wrapper">
          <div className="page-content">
            <div className="module-stack">
              <HeroFingerprint variant="loading" />
              <PlayerStanding variant="loading" />
              <TheRoomOnPlayer variant="loading" />
              <SignatureStory variant="loading" />
              <CurrentSeasonProduction variant="loading" />
              <AdvancedSavantCard variant="loading" />
              <Splits variant="loading" />
              <PeerComparator variant="loading" />
              <SupportingCast variant="loading" />
              <BioRecruitingTransferRoster variant="loading" />
            </div>
          </div>
        </div>
        <style>
          {`
            .page-wrapper {
              container-type: inline-size;
            }

            .page-content {
              max-width: 1440px;
              margin: 0 auto;
              padding: var(--space-12);
            }

            @container (max-width: 768px) {
              .page-content {
                padding: var(--space-8);
              }
            }

            @container (max-width: 375px) {
              .page-content {
                padding: var(--space-4);
              }
            }

            .module-stack {
              display: flex;
              flex-direction: column;
              gap: var(--space-12);
            }
          `}
        </style>
      </div>
    );
  }

  // Partial state
  if (variant === 'partial') {
    const partialAnchors: SubnavAnchor[] = [
      { id: 'hero', label: 'Hero', href: '#hero' },
      { id: 'standing', label: 'Standing', href: '#standing' },
      { id: 'room', label: 'Room', href: '#room' },
      { id: 'story', label: 'Story', href: '#story' },
      { id: 'production', label: 'Production', href: '#production' },
      { id: 'savant', label: 'Savant', href: '#savant' },
      { id: 'splits', label: 'Splits', href: '#splits' },
      { id: 'peers', label: 'Peers', href: '#peers' },
      { id: 'cast', label: 'Cast', href: '#cast' },
      { id: 'bio', label: 'Bio', href: '#bio' },
    ];

    return (
      <div className="dark min-h-screen bg-background">
        <Subnav
          playerName="CJ Carr"
          playerTeam="Notre Dame"
          playerPosition="QB"
          anchors={partialAnchors}
          currentSection="hero"
          isSticky={false}
        />
        <div className="page-wrapper">
          <div className="page-content">
            <div className="module-stack">
              <HeroFingerprint />
              <PlayerStanding />
              <TheRoomOnPlayer variant="partial" />
              <SignatureStory variant="loading" />
              <CurrentSeasonProduction variant="partial" />
              <AdvancedSavantCard variant="partial" />
              <Splits variant="partial" />
              <PeerComparator variant="loading" />
              <SupportingCast variant="partial" />
              <BioRecruitingTransferRoster variant="partial" />
            </div>
          </div>
        </div>
        <style>
          {`
            .page-wrapper {
              container-type: inline-size;
            }

            .page-content {
              max-width: 1440px;
              margin: 0 auto;
              padding: var(--space-12);
            }

            @container (max-width: 768px) {
              .page-content {
                padding: var(--space-8);
              }
            }

            @container (max-width: 375px) {
              .page-content {
                padding: var(--space-4);
              }
            }

            .module-stack {
              display: flex;
              flex-direction: column;
              gap: var(--space-12);
            }
          `}
        </style>
      </div>
    );
  }

  // Full state
  const { searchParams, updateParam } = useURLState();
  const [currentSection, setCurrentSection] = useState<string>('section-hero');
  const [isSubnavSticky, setIsSubnavSticky] = useState(false);
  const heroRef = useRef<HTMLDivElement>(null);
  const standingRef = useRef<HTMLDivElement>(null);
  const roomRef = useRef<HTMLDivElement>(null);
  const storyRef = useRef<HTMLDivElement>(null);
  const productionRef = useRef<HTMLDivElement>(null);
  const savantRef = useRef<HTMLDivElement>(null);
  const splitsRef = useRef<HTMLDivElement>(null);
  const peersRef = useRef<HTMLDivElement>(null);
  const castRef = useRef<HTMLDivElement>(null);
  const bioRef = useRef<HTMLDivElement>(null);

  // Extract URL params for interactive modules
  const savantCohort = (searchParams.get('savant') as 'p4' | 'g5' | 'all-fbs') || 'p4';
  const roomCohort = (searchParams.get('room') as 'own' | 'rival' | 'national' | 'media') || 'own';
  const bioTab = (searchParams.get('bio') as 'bio' | 'recruiting' | 'transfer' | 'roster') || 'bio';
  const splitsTab = searchParams.get('splits') || undefined;
  const standingRung = searchParams.get('standing') || undefined;
  const peersSearch = searchParams.get('peers') || undefined;

  const anchors: SubnavAnchor[] = [
    { id: 'section-hero', label: 'Hero', href: '#section-hero' },
    { id: 'section-standing', label: 'Standing', href: '#section-standing' },
    { id: 'section-room', label: 'Room', href: '#section-room' },
    { id: 'section-story', label: 'Story', href: '#section-story' },
    { id: 'section-production', label: 'Production', href: '#section-production' },
    { id: 'section-savant', label: 'Savant', href: '#section-savant' },
    { id: 'section-splits', label: 'Splits', href: '#section-splits' },
    { id: 'section-peers', label: 'Peers', href: '#section-peers' },
    { id: 'section-cast', label: 'Cast', href: '#section-cast' },
    { id: 'section-bio', label: 'Bio', href: '#section-bio' },
  ];

  // IntersectionObserver for current section tracking
  useEffect(() => {
    const sections = [
      { id: 'section-hero', ref: heroRef },
      { id: 'section-standing', ref: standingRef },
      { id: 'section-room', ref: roomRef },
      { id: 'section-story', ref: storyRef },
      { id: 'section-production', ref: productionRef },
      { id: 'section-savant', ref: savantRef },
      { id: 'section-splits', ref: splitsRef },
      { id: 'section-peers', ref: peersRef },
      { id: 'section-cast', ref: castRef },
      { id: 'section-bio', ref: bioRef },
    ];

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const sectionId = entry.target.id;
            if (sectionId) {
              setCurrentSection(sectionId);
            }
          }
        });
      },
      { threshold: 0.3, rootMargin: '-20% 0px -60% 0px' }
    );

    sections.forEach(({ ref }) => {
      if (ref.current) {
        observer.observe(ref.current);
      }
    });

    return () => observer.disconnect();
  }, []);

  // IntersectionObserver for sticky subnav (becomes sticky after Hero exits)
  useEffect(() => {
    if (!heroRef.current) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        setIsSubnavSticky(!entry.isIntersecting);
      },
      { threshold: 0 }
    );

    observer.observe(heroRef.current);
    return () => observer.disconnect();
  }, []);

  const handleAnchorClick = (anchorId: string) => {
    const section = document.getElementById(anchorId);
    if (section) {
      section.scrollIntoView({
        behavior: 'smooth',
        block: 'start',
      });
    }
  };

  const handleJumpToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="dark min-h-screen bg-background">
      <Subnav
        playerName="CJ Carr"
        playerTeam="Notre Dame"
        playerPosition="QB"
        anchors={anchors}
        currentSection={currentSection}
        isSticky={isSubnavSticky}
        onAnchorClick={handleAnchorClick}
        onJumpToTop={handleJumpToTop}
      />
      <div className="page-wrapper">
        <div className="page-content">
          <div className="module-stack">
            <div ref={heroRef} id="section-hero">
              <HeroFingerprint />
            </div>
            <div ref={standingRef} id="section-standing">
              <PlayerStanding />
            </div>
            <div ref={roomRef} id="section-room">
              <TheRoomOnPlayer
                initialCohort={roomCohort}
                onCohortChange={(cohort) => updateParam('room', cohort)}
              />
            </div>
            <div ref={storyRef} id="section-story">
              <SignatureStory />
            </div>
            <div ref={productionRef} id="section-production">
              <CurrentSeasonProduction />
            </div>
            <div ref={savantRef} id="section-savant">
              <AdvancedSavantCard
                cohort={savantCohort}
                onCohortChange={(cohort) => updateParam('savant', cohort)}
              />
            </div>
            <div ref={splitsRef} id="section-splits">
              <Splits />
            </div>
            <div ref={peersRef} id="section-peers">
              <PeerComparator />
            </div>
            <div ref={castRef} id="section-cast">
              <SupportingCast />
            </div>
            <div ref={bioRef} id="section-bio">
              <BioRecruitingTransferRoster
                initialTab={bioTab}
                onTabChange={(tab) => updateParam('bio', tab)}
              />
            </div>
          </div>
        </div>
      </div>
      <style>
        {`
          .page-wrapper {
            container-type: inline-size;
          }

          .page-content {
            max-width: 1440px;
            margin: 0 auto;
            padding: var(--space-12);
          }

          @container (max-width: 768px) {
            .page-content {
              padding: var(--space-8);
            }
          }

          @container (max-width: 375px) {
            .page-content {
              padding: var(--space-4);
            }
          }

          .module-stack {
            display: flex;
            flex-direction: column;
            gap: var(--space-12);
          }

          html {
            scroll-behavior: smooth;
          }

          @media (prefers-reduced-motion: reduce) {
            html {
              scroll-behavior: auto;
            }
          }
        `}
      </style>
    </div>
  );
}
