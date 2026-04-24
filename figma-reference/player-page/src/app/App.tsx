import PlayerPage from './pages/PlayerPage';
import StandingVariants from './components/StandingVariants';

export default function App() {
  return (
    <div className="dark min-h-screen bg-background">
      <div style={{ padding: 'var(--space-8)' }}>
        {/* Section headers with spacing */}
        <div style={{ marginBottom: 'var(--space-12)' }}>
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
            CFB INDEX PLAYER PAGE
          </h1>
          <p style={{ color: 'oklch(0.6 0.02 250)', fontSize: 'var(--fs-body)' }}>
            Stage 3: Full page flow · 1440 / 768 / 375
          </p>
        </div>

        {/* Three-column breakpoint layout */}
        <section style={{ marginBottom: 'var(--space-16)' }}>
          <div className="breakpoint-grid">
            {/* Desktop 1440 */}
            <div>
              <h2
                className="leading-none tracking-tight uppercase"
                style={{
                  fontFamily: 'var(--font-display)',
                  color: 'oklch(0.95 0.01 250)',
                  fontWeight: 600,
                  fontSize: 'var(--fs-h2)',
                  marginBottom: 'var(--space-6)',
                }}
              >
                DESKTOP 1440
              </h2>
              <div className="max-w-[1440px]">
                <PlayerPage />
              </div>
            </div>

            {/* Tablet 768 */}
            <div>
              <h2
                className="leading-none tracking-tight uppercase"
                style={{
                  fontFamily: 'var(--font-display)',
                  color: 'oklch(0.95 0.01 250)',
                  fontWeight: 600,
                  fontSize: 'var(--fs-h2)',
                  marginBottom: 'var(--space-6)',
                }}
              >
                TABLET 768
              </h2>
              <div className="max-w-[768px]">
                <PlayerPage />
              </div>
            </div>

            {/* Mobile 375 */}
            <div>
              <h2
                className="leading-none tracking-tight uppercase"
                style={{
                  fontFamily: 'var(--font-display)',
                  color: 'oklch(0.95 0.01 250)',
                  fontWeight: 600,
                  fontSize: 'var(--fs-h2)',
                  marginBottom: 'var(--space-6)',
                }}
              >
                MOBILE 375
              </h2>
              <div className="max-w-[375px]">
                <PlayerPage />
              </div>
            </div>
          </div>
        </section>

        {/* Page-level states */}
        <section style={{ marginBottom: 'var(--space-16)' }}>
          <h2
            className="leading-none tracking-tight uppercase"
            style={{
              fontFamily: 'var(--font-display)',
              color: 'oklch(0.95 0.01 250)',
              fontWeight: 600,
              fontSize: 'var(--fs-h1)',
              marginBottom: 'var(--space-6)',
            }}
          >
            PAGE-LEVEL STATES
          </h2>
          <div className="breakpoint-grid">
            <div>
              <h3
                className="text-sm font-semibold uppercase"
                style={{ color: 'oklch(0.6 0.02 250)', marginBottom: 'var(--space-4)' }}
              >
                Loading
              </h3>
              <div className="max-w-[1440px]">
                <PlayerPage variant="loading" />
              </div>
            </div>
            <div>
              <h3
                className="text-sm font-semibold uppercase"
                style={{ color: 'oklch(0.6 0.02 250)', marginBottom: 'var(--space-4)' }}
              >
                Partial
              </h3>
              <div className="max-w-[1440px]">
                <PlayerPage variant="partial" />
              </div>
            </div>
            <div>
              <h3
                className="text-sm font-semibold uppercase"
                style={{ color: 'oklch(0.6 0.02 250)', marginBottom: 'var(--space-4)' }}
              >
                Error
              </h3>
              <div className="max-w-[1440px]">
                <PlayerPage variant="error" playerId="invalid-xyz" />
              </div>
            </div>
          </div>
        </section>

        {/* Standing Variants Board */}
        <section>
          <div className="max-w-[1440px]">
            <StandingVariants />
          </div>
        </section>
      </div>

      <style>
        {`
          .breakpoint-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: var(--space-12);
          }

          @media (min-width: 1400px) {
            .breakpoint-grid {
              grid-template-columns: repeat(3, 1fr);
            }
          }
        `}
      </style>
    </div>
  );
}