-- Sprint v5-1 patch: add conference_slug column to conferences table.
--
-- Bug context: 4 code sites query `conferences.conference_slug` or
-- `c.conference_slug = ?` but the column never existed in the conferences
-- table schema:
--   - src/cfb_rankings/team_pages/pulse_themes.py:77 (_fetch_conference_excerpts)
--   - src/cfb_rankings/conferences_pulse/renderer.py:58, 113
--   - src/cfb_rankings/reporting.py:3040 (LEFT JOIN conferences)
--
-- Each one fails sqlite3.OperationalError: no such column: c.conference_slug
-- masked by the set+e || echo "X failed (continuing)" anti-pattern. Pulse
-- themes for conference entities (SEC, Big Ten, ACC, etc.) were silently
-- producing zero output on every world_class_enrich run.
--
-- Discovered 2026-05-15 from world_class_enrich.yml run 25942058001.
--
-- The slug-to-short_name mapping is defined in
-- src/cfb_rankings/conferences_pulse/renderer.py:36-50 (_CONF_DISPLAY).
-- Backfilling here so existing rows match.

ALTER TABLE conferences ADD COLUMN conference_slug TEXT;

-- Backfill from the canonical mapping in _CONF_DISPLAY. Unknown
-- conferences fall through to a generic lower-kebab-case of short_name.
UPDATE conferences SET conference_slug = CASE conference_short_name
    WHEN 'SEC'                 THEN 'sec'
    WHEN 'Big Ten'             THEN 'fbs-big-ten'
    WHEN 'ACC'                 THEN 'acc'
    WHEN 'Big 12'              THEN 'big-12'
    WHEN 'American Athletic'   THEN 'american-athletic'
    WHEN 'American'            THEN 'american-athletic'
    WHEN 'Mountain West'       THEN 'mountain-west'
    WHEN 'Conference USA'      THEN 'conference-usa'
    WHEN 'C-USA'               THEN 'conference-usa'
    WHEN 'Sun Belt'            THEN 'sun-belt'
    WHEN 'MAC'                 THEN 'fbs-mac'
    WHEN 'Mid-American'        THEN 'fbs-mac'
    WHEN 'Pac-12'              THEN 'pac-12'
    WHEN 'Pacific 12'          THEN 'pac-12'
    WHEN 'FBS Independents'    THEN 'fbs-independents'
    WHEN 'Independent'         THEN 'fbs-independents'
    WHEN 'SWAC'                THEN 'swac'
    WHEN 'MEAC'                THEN 'meac'
    WHEN 'CAA'                 THEN 'caa'
    WHEN 'Big Sky'             THEN 'big-sky'
    WHEN 'Patriot'             THEN 'patriot'
    WHEN 'Pioneer'             THEN 'pioneer'
    WHEN 'Ivy'                 THEN 'ivy'
    WHEN 'NEC'                 THEN 'nec'
    WHEN 'OVC'                 THEN 'ovc'
    WHEN 'Southern'            THEN 'southern'
    WHEN 'Southland'           THEN 'southland'
    WHEN 'Big South'           THEN 'big-south'
    WHEN 'Missouri Valley'     THEN 'missouri-valley'
    WHEN 'United Athletic'     THEN 'united-athletic'
    ELSE LOWER(REPLACE(REPLACE(REPLACE(conference_short_name, ' ', '-'), '/', '-'), '.', ''))
END;

CREATE INDEX IF NOT EXISTS idx_conferences_slug ON conferences(conference_slug);
