// Subnav primitive — sticky horizontal nav with section anchors
// States: not-sticky, sticky, anchor-selected, mobile-collapsed, loading

import { useState, useEffect, useRef } from 'react';

export interface SubnavAnchor {
  id: string;
  label: string;
  href: string;
}

interface SubnavProps {
  /** Player identity for left strip */
  playerName: string;
  playerTeam: string;
  playerPosition: string;
  /** Section anchors for center */
  anchors: SubnavAnchor[];
  /** Current active section ID */
  currentSection?: string;
  /** Sticky state (controlled externally via IntersectionObserver) */
  isSticky: boolean;
  /** Loading state (non-interactive) */
  isLoading?: boolean;
  /** Click handler for anchors */
  onAnchorClick?: (anchorId: string) => void;
  /** Click handler for jump-to-top */
  onJumpToTop?: () => void;
}

export function Subnav({
  playerName,
  playerTeam,
  playerPosition,
  anchors,
  currentSection,
  isSticky,
  isLoading = false,
  onAnchorClick,
  onJumpToTop,
}: SubnavProps) {
  const [isMobile, setIsMobile] = useState(false);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  // Detect mobile layout via container query simulation
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth <= 768);
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // Auto-scroll current anchor into view on mobile
  useEffect(() => {
    if (isMobile && currentSection && scrollContainerRef.current) {
      const activeButton = scrollContainerRef.current.querySelector(
        `[data-anchor-id="${currentSection}"]`
      ) as HTMLElement;
      if (activeButton) {
        activeButton.scrollIntoView({
          behavior: 'smooth',
          block: 'nearest',
          inline: 'center',
        });
      }
    }
  }, [currentSection, isMobile]);

  // Generate monogram from player name (first initial + last initial)
  const generateMonogram = (name: string) => {
    const parts = name.split(' ');
    if (parts.length >= 2) {
      return `${parts[0][0]}${parts[parts.length - 1][0]}`;
    }
    return name.substring(0, 2).toUpperCase();
  };

  const monogram = generateMonogram(playerName);

  return (
    <nav
      className={`subnav ${isSticky ? 'subnav-sticky' : 'subnav-not-sticky'} ${isMobile ? 'subnav-mobile' : 'subnav-desktop'}`}
      aria-label="Player page sections"
      style={{
        position: isSticky ? 'sticky' : 'static',
        top: isSticky ? 0 : 'auto',
        zIndex: isSticky ? 100 : 'auto',
        background: 'oklch(0.18 0.01 250)',
        borderBottom: isSticky ? '1px solid oklch(0.25 0.01 250)' : 'none',
        boxShadow: isSticky ? 'var(--elevation-2)' : 'none',
        transition: 'box-shadow var(--motion-state), border-color var(--motion-state)',
        containerType: 'inline-size',
      }}
    >
      <div
        className="subnav-content"
        style={{
          maxWidth: '1440px',
          margin: '0 auto',
          padding: 'var(--space-4) var(--space-8)',
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--space-6)',
        }}
      >
        {/* Left: Player identity strip */}
        {!isMobile && (
          <div className="subnav-identity" style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
            <div
              className="monogram"
              style={{
                width: '2rem',
                height: '2rem',
                borderRadius: '50%',
                background: 'oklch(0.3 0.01 250)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontFamily: 'var(--font-display)',
                fontSize: '0.75rem',
                fontWeight: 700,
                color: 'oklch(0.95 0.01 250)',
              }}
            >
              {monogram}
            </div>
            <div>
              <div
                className="font-semibold"
                style={{
                  fontFamily: 'var(--font-display)',
                  fontSize: 'var(--fs-body)',
                  color: 'oklch(0.95 0.01 250)',
                  lineHeight: 1.2,
                }}
              >
                {playerName}
              </div>
              <div
                className="text-xs"
                style={{
                  color: 'oklch(0.6 0.02 250)',
                }}
              >
                {playerPosition} · {playerTeam}
              </div>
            </div>
          </div>
        )}

        {/* Center: Section anchors */}
        <div
          className="subnav-anchors"
          ref={scrollContainerRef}
          style={{
            flex: 1,
            display: 'flex',
            gap: isMobile ? 'var(--space-2)' : 'var(--space-3)',
            overflowX: isMobile ? 'auto' : 'visible',
            scrollSnapType: isMobile ? 'x mandatory' : 'none',
            WebkitOverflowScrolling: 'touch',
            scrollbarWidth: 'none',
            msOverflowStyle: 'none',
          }}
        >
          {anchors.map((anchor) => {
            const isActive = currentSection === anchor.id;
            return (
              <button
                key={anchor.id}
                type="button"
                data-anchor-id={anchor.id}
                onClick={() => !isLoading && onAnchorClick?.(anchor.id)}
                disabled={isLoading}
                aria-current={isActive ? 'page' : undefined}
                className="text-xs font-semibold tracking-wider uppercase"
                style={{
                  padding: isMobile ? 'var(--space-2) var(--space-4)' : 'var(--space-2) var(--space-3)',
                  background: isActive ? 'oklch(0.3 0.01 250)' : 'transparent',
                  color: isActive ? 'oklch(0.95 0.01 250)' : isLoading ? 'oklch(0.5 0.02 250)' : 'oklch(0.7 0.02 250)',
                  border: isActive ? 'none' : '1px solid oklch(0.28 0.01 250)',
                  borderRadius: '999px',
                  letterSpacing: '0.08em',
                  transition: 'background var(--motion-state), color var(--motion-state)',
                  cursor: isLoading ? 'default' : 'pointer',
                  whiteSpace: 'nowrap',
                  scrollSnapAlign: isMobile ? 'center' : 'none',
                  minHeight: '44px',
                  flexShrink: 0,
                }}
              >
                {anchor.label}
              </button>
            );
          })}
        </div>

        {/* Right: Jump to top */}
        {!isMobile && (
          <button
            type="button"
            onClick={() => !isLoading && onJumpToTop?.()}
            disabled={isLoading}
            className="text-xs font-semibold tracking-wider uppercase"
            style={{
              padding: 'var(--space-2) var(--space-4)',
              background: 'transparent',
              color: isLoading ? 'oklch(0.5 0.02 250)' : 'oklch(0.7 0.02 250)',
              border: '1px solid oklch(0.28 0.01 250)',
              borderRadius: '999px',
              letterSpacing: '0.08em',
              transition: 'color var(--motion-state)',
              cursor: isLoading ? 'default' : 'pointer',
              minHeight: '44px',
            }}
          >
            ↑ Top
          </button>
        )}
      </div>

      <style>
        {`
          .subnav-anchors::-webkit-scrollbar {
            display: none;
          }
        `}
      </style>
    </nav>
  );
}
