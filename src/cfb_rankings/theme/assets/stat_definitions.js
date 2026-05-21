/**
 * Stat Definitions Module (World-Class CFB Stats Display)
 * -----------------------------------------------------------------------
 * Tap-triggered stat definitions with bottom sheet (mobile) / popover (desktop).
 *
 * Advanced stat headers are tappable to reveal:
 *   - One-sentence plain-English definition
 *   - Formula (in monospace)
 *   - "Leaders typically range from X to Y" benchmark
 *   - Link to methodology page
 *
 * Spec: docs/research/cfb-stats-conformance-spec.md §3.1
 * Mobile Playbook: docs/research/cfb-stats-mobile-playbook.md §10
 */

(function() {
  'use strict';

  // ===========================================================================
  // DEFINITION CONTENT
  // ===========================================================================

  const STAT_DEFINITIONS = {
    // Passing efficiency metrics
    'cmp': {
      name: 'Completions',
      definition: 'Completed passes.',
      formula: null,
      benchmark: null,
    },
    'att': {
      name: 'Attempts',
      definition: 'Pass attempts.',
      formula: null,
      benchmark: null,
    },
    'cmp_pct': {
      name: 'Completion Percentage',
      definition: 'Completions divided by pass attempts.',
      formula: 'CMP / ATT',
      benchmark: 'Leaders typically range from 65% to 75%.',
    },
    'yds_per_att': {
      name: 'Yards per Attempt',
      definition: 'Yards gained per pass attempt, including sacks.',
      formula: 'Passing Yards / Attempts',
      benchmark: 'Leaders typically range from 8.5 to 12.0.',
    },
    'rate': {
      name: 'Passer Rating',
      definition: 'NCAA pass efficiency formula (not ESPN QBR).',
      formula: '(CMP * 100) + (YDS * 8.4) + (TD * 330) + (INT * -200) / ATT',
      benchmark: 'Leaders typically range from 150 to 200.',
    },
    'lng': {
      name: 'Longest',
      definition: 'Longest pass play of the season.',
      formula: null,
      benchmark: null,
    },
    'td': {
      name: 'Touchdown Passes',
      definition: 'Touchdown passes thrown.',
      formula: null,
      benchmark: 'Leaders typically throw 30-40+ TDs.',
    },
    'int': {
      name: 'Interceptions',
      definition: 'Interceptions thrown.',
      formula: null,
      benchmark: 'Elite QBs throw fewer than 10 INTs per season.',
    },
    'sack': {
      name: 'Times Sacked',
      definition: 'Number of times sacked.',
      formula: null,
      benchmark: null,
    },

    // Rushing metrics
    'yds': {
      name: 'Yards',
      definition: 'Total rushing yards.',
      formula: null,
      benchmark: 'Leaders typically range from 1,200 to 2,000+ yards.',
    },
    'yds_per_gm': {
      name: 'Yards per Game',
      definition: 'Rushing yards per game played.',
      formula: 'Rushing Yards / Games Played',
      benchmark: 'Leaders typically range from 80 to 150 yards per game.',
    },

    // Receiving metrics
    'rec': {
      name: 'Receptions',
      definition: 'Pass receptions.',
      formula: null,
      benchmark: 'Leaders typically catch 80-120+ passes.',
    },
    'yds_per_rec': {
      name: 'Yards per Reception',
      definition: 'Yards gained per catch.',
      formula: 'Receiving Yards / Receptions',
      benchmark: 'Leaders typically range from 14 to 20 yards per catch.',
    },

    // Team offense metrics
    'pts_per_gm': {
      name: 'Points per Game',
      definition: 'Points scored per game.',
      formula: 'Total Points / Games Played',
      benchmark: 'Elite offenses score 35+ points per game.',
    },
    'yds_per_play': {
      name: 'Yards per Play',
      definition: 'Yards gained per offensive play.',
      formula: 'Total Yards / Total Plays',
      benchmark: 'Elite offenses gain 6.5+ yards per play.',
    },
    'third_down_pct': {
      name: 'Third Down %',
      definition: 'Third down conversion rate.',
      formula: 'Third Down Conversions / Third Down Attempts',
      benchmark: 'Elite offenses convert 45%+ of third downs.',
    },
    'fourth_down_pct': {
      name: 'Fourth Down %',
      definition: 'Fourth down conversion rate.',
      formula: 'Fourth Down Conversions / Fourth Down Attempts',
      benchmark: 'Elite offenses convert 60%+ of fourth downs.',
    },
    'red_zone_pct': {
      name: 'Red Zone %',
      definition: 'Red zone touchdown rate.',
      formula: 'Red Zone TDs / Red Zone Attempts',
      benchmark: 'Elite offenses score TDs on 75%+ of red zone trips.',
    },
    'turnovers': {
      name: 'Turnovers',
      definition: 'Total turnovers lost (fumbles + interceptions).',
      formula: null,
      benchmark: 'Elite teams commit fewer than 15 turnovers per season.',
    },

    // Advanced analytics
    'epa_per_play': {
      name: 'EPA per Play',
      definition: 'Expected points added per play; measures scoreboard value of each snap.',
      formula: 'Sum of EPA on all plays / Total Plays',
      benchmark: 'Elite offenses average +0.25 EPA/play; poor offenses are negative.',
    },
    'success_rate': {
      name: 'Success Rate',
      definition: 'Share of plays that keep the offense on schedule (50% on 1st, 70% on 2nd, 100% on 3rd/4th).',
      formula: 'Successful Plays / Total Plays',
      benchmark: 'Elite offenses succeed on 48%+ of plays.',
    },
    'cpoe': {
      name: 'CPOE',
      definition: 'Completion percentage over expected, adjusted for throw depth and pressure.',
      formula: 'Actual Completion % - Expected Completion %',
      benchmark: 'Elite QBs are +5% or higher; poor QBs are negative.',
    },
    'aya': {
      name: 'Adjusted Yards/Attempt',
      definition: 'Adjusted yards per attempt; folds TD (+20) and INT (-45) value into passing efficiency.',
      formula: '(Yards + (TD * 20) - (INT * 45)) / Attempts',
      benchmark: 'Elite QBs average 9.0+ AY/A.',
    },
    'any_a': {
      name: 'Adjusted Net Yards/Attempt',
      definition: 'Like AY/A but with sack yardage subtracted; the most complete single-number passer metric.',
      formula: '(Yards - Sack Yards + (TD * 20) - (INT * 45)) / (Attempts + Sacks)',
      benchmark: 'Rare in CFB; elite NFL QBs average 7.5+ ANY/A.',
    },
    'explosiveness': {
      name: 'Explosiveness',
      definition: 'Average EPA on successful plays; measures big-play capability.',
      formula: 'Sum of EPA on successful plays / Successful plays',
      benchmark: 'Top offenses post 1.3+ explosiveness; floor is around 1.0.',
    },

    // Defensive metrics (conformance spec §1.4-1.6)
    'tkl': {
      name: 'Total Tackles',
      definition: 'Solo tackles plus assisted tackles. The volume metric for defensive players.',
      formula: 'SOLO + AST',
      benchmark: 'Linebacker leaders post 120+ tackles; safeties 90+; corners 60+.',
    },
    'solo': {
      name: 'Solo Tackles',
      definition: 'Unassisted tackles credited fully to one player.',
      formula: null,
      benchmark: null,
    },
    'ast': {
      name: 'Assisted Tackles',
      definition: 'Tackles credited as an assist (half-tackle in NCAA accounting).',
      formula: null,
      benchmark: null,
    },
    'tfl': {
      name: 'Tackles for Loss',
      definition: 'Tackles behind the line of scrimmage. Sacks ARE counted as TFLs in the NCAA convention; this stat reports both.',
      formula: null,
      benchmark: 'Edge-rusher leaders post 18-25 TFL; interior DL 12-18.',
    },
    'qbh': {
      name: 'QB Hurries',
      definition: 'Pressures applied to the quarterback that did not result in a sack. Tracked inconsistently across data providers.',
      formula: null,
      benchmark: null,
    },
    'ff': {
      name: 'Forced Fumbles',
      definition: 'Strips of the ball by the defender that resulted in a fumble (regardless of who recovered).',
      formula: null,
      benchmark: null,
    },
    'fr': {
      name: 'Fumble Recoveries',
      definition: 'Loose-ball recoveries by the defender. Some sources also track fumble-recovery yardage and TDs.',
      formula: null,
      benchmark: null,
    },
    'pd': {
      name: 'Pass Deflections',
      definition: 'Passes broken up at the line or in coverage (also called "PBU" in NFL convention).',
      formula: null,
      benchmark: 'Cornerback leaders post 12-18 PD; safeties typically lower.',
    },
    'pass_def': {
      name: 'Passes Defended',
      definition: 'NCAA summary metric: interceptions plus pass deflections.',
      formula: 'INT + PD',
      benchmark: 'Elite corners post 18+ passes defended.',
    },
    'int_yds': {
      name: 'Interception Return Yards',
      definition: 'Yards gained on interception returns.',
      formula: null,
      benchmark: null,
    },
    'int_td': {
      name: 'Pick-Sixes',
      definition: 'Interceptions returned for a touchdown.',
      formula: null,
      benchmark: null,
    },

    // Kicking metrics (conformance spec §1.7)
    'fgm': {
      name: 'Field Goals Made',
      definition: 'Successful field goal attempts.',
      formula: null,
      benchmark: 'Volume leaders post 25+ FGM; elite kickers 80%+ make rate.',
    },
    'fga': {
      name: 'Field Goals Attempted',
      definition: 'Total field goal attempts including misses.',
      formula: null,
      benchmark: null,
    },
    'fg_pct': {
      name: 'Field Goal Percentage',
      definition: 'Make rate across all field goal attempts.',
      formula: 'FGM / FGA',
      benchmark: 'Elite kickers convert 85%+ overall; 70%+ from 40-49; 50%+ from 50+.',
    },
    'xpm': {
      name: 'Extra Points Made',
      definition: 'Successful PAT kicks (one-point conversions only; 2-point tries tracked separately).',
      formula: null,
      benchmark: null,
    },
    'xpa': {
      name: 'Extra Points Attempted',
      definition: 'Total PAT kick attempts.',
      formula: null,
      benchmark: null,
    },
    'xp_pct': {
      name: 'Extra Point Percentage',
      definition: 'Make rate on PAT kick attempts. Elite kickers are above 98%.',
      formula: 'XPM / XPA',
      benchmark: null,
    },

    // Punting metrics (conformance spec §1.8)
    'punt_avg': {
      name: 'Punting Average',
      definition: 'Gross yards per punt. Pure-punting context only; do not use `AVG` in mixed tables.',
      formula: 'Gross Yards / Punts',
      benchmark: 'Elite punters average 45+ yards per punt.',
    },
    'net': {
      name: 'Net Punting Average',
      definition: 'Punting average after subtracting return yards and touchback penalties.',
      formula: '(Gross Yards - Return Yards - 20×Touchbacks) / Punts',
      benchmark: 'Elite punters net 40+ yards.',
    },
    'i20': {
      name: 'Inside the 20',
      definition: 'Punts downed inside the opponent 20-yard line. Field-position weapon.',
      formula: null,
      benchmark: 'Elite punters post 25+ I20 per season.',
    },
    'tb': {
      name: 'Touchbacks',
      definition: 'Punts ending in the end zone. Lower is better for punters.',
      formula: null,
      benchmark: null,
    },

    // Return metrics (conformance spec §1.9)
    'kr_avg': {
      name: 'Kick Return Average',
      definition: 'Yards per kick return.',
      formula: 'KR Yards / KR Returns',
      benchmark: 'Elite returners average 25+ yards per return.',
    },
    'pr_avg': {
      name: 'Punt Return Average',
      definition: 'Yards per punt return.',
      formula: 'PR Yards / PR Returns',
      benchmark: 'Elite punt returners average 12+ yards.',
    },
  };

  // ===========================================================================
  // BOTTOM SHEET RENDERER (Mobile)
  // ===========================================================================

  function createBottomSheet(statId) {
    const def = STAT_DEFINITIONS[statId];
    if (!def) return null;

    const sheet = document.createElement('div');
    sheet.className = 'wcfb-stats-bottom-sheet';
    sheet.setAttribute('role', 'dialog');
    sheet.setAttribute('aria-labelledby', 'wcfb-stats-def-title');
    sheet.setAttribute('aria-modal', 'true');

    let content = `
      <div class="wcfb-stats-bottom-sheet__backdrop"></div>
      <div class="wcfb-stats-bottom-sheet__content" role="document">
        <div class="wcfb-stats-bottom-sheet__header">
          <h2 id="wcfb-stats-def-title" class="wcfb-stats-bottom-sheet__title">${def.name}</h2>
          <button type="button" class="wcfb-stats-bottom-sheet__close" aria-label="Close definition">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path d="M4.707 4.707a1 1 0 011.414 0L10 8.586l3.879-3.879a1 1 0 111.414 1.414L11.414 10l3.879 3.879a1 1 0 01-1.414 1.414L10 11.414l-3.879 3.879a1 1 0 01-1.414-1.414L8.586 10 4.707 6.121a1 1 0 010-1.414z"/>
            </svg>
          </button>
        </div>
        <div class="wcfb-stats-bottom-sheet__body">
          <p class="wcfb-stats-bottom-sheet__definition">${def.definition}</p>
    `;

    if (def.formula) {
      content += `  <p class="wcfb-stats-bottom-sheet__formula"><code>${def.formula}</code></p>`;
    }

    if (def.benchmark) {
      content += `  <p class="wcfb-stats-bottom-sheet__benchmark">${def.benchmark}</p>`;
    }

    content += `
          <a href="/methodology/#stats-glossary" class="wcfb-stats-bottom-sheet__link">View full glossary →</a>
        </div>
      </div>
    `;

    sheet.innerHTML = content;

    // Close handlers
    const backdrop = sheet.querySelector('.wcfb-stats-bottom-sheet__backdrop');
    const closeBtn = sheet.querySelector('.wcfb-stats-bottom-sheet__close');

    const close = () => {
      sheet.classList.remove('wcfb-stats-bottom-sheet--open');
      setTimeout(() => sheet.remove(), 300);
    };

    backdrop.addEventListener('click', close);
    closeBtn.addEventListener('click', close);

    // Escape key closes
    sheet.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') close();
    });

    return sheet;
  }

  // ===========================================================================
  // POPOVER RENDERER (Desktop)
  // ===========================================================================

  function createPopover(statId, targetEl) {
    const def = STAT_DEFINITIONS[statId];
    if (!def) return null;

    const popover = document.createElement('div');
    popover.className = 'wcfb-stats-popover';
    popover.setAttribute('role', 'tooltip');
    popover.id = `wcfb-stats-popover-${statId}`;

    let content = `
      <div class="wcfb-stats-popover__content">
        <strong class="wcfb-stats-popover__title">${def.name}</strong>
        <p class="wcfb-stats-popover__definition">${def.definition}</p>
    `;

    if (def.formula) {
      content += `  <p class="wcfb-stats-popover__formula"><code>${def.formula}</code></p>`;
    }

    if (def.benchmark) {
      content += `  <p class="wcfb-stats-popover__benchmark">${def.benchmark}</p>`;
    }

    content += `  <a href="/methodology/#stats-glossary" class="wcfb-stats-popover__link">More →</a>`;
    content += `</div>`;

    popover.innerHTML = content;

    // Position popover above target
    const rect = targetEl.getBoundingClientRect();
    popover.style.position = 'fixed';
    popover.style.bottom = `${window.innerHeight - rect.top + 8}px`;
    popover.style.left = `${rect.left + (rect.width / 2)}px`;
    popover.style.transform = 'translateX(-50%)';

    return popover;
  }

  // ===========================================================================
  // INTERACTION HANDLERS
  // ===========================================================================

  function handleStatTriggerClick(event) {
    const trigger = event.target.closest('[data-def]');
    if (!trigger) return;

    const statId = trigger.getAttribute('data-def');
    if (!statId) return;

    event.preventDefault();
    event.stopPropagation();

    // Check viewport width for mobile vs desktop
    const isMobile = window.innerWidth < 768;

    if (isMobile) {
      // Mobile: show bottom sheet
      const existingSheet = document.querySelector('.wcfb-stats-bottom-sheet');
      if (existingSheet) existingSheet.remove();

      const sheet = createBottomSheet(statId);
      if (sheet) {
        document.body.appendChild(sheet);
        // Trigger reflow for animation
        sheet.offsetHeight;
        sheet.classList.add('wcfb-stats-bottom-sheet--open');
      }
    } else {
      // Desktop: show popover
      const existingPopover = document.querySelector('.wcfb-stats-popover');
      if (existingPopover) existingPopover.remove();

      const popover = createPopover(statId, trigger);
      if (popover) {
        document.body.appendChild(popover);
        trigger.setAttribute('aria-describedby', popover.id);

        // Auto-dismiss on click outside
        const dismiss = (e) => {
          if (!popover.contains(e.target) && !trigger.contains(e.target)) {
            popover.remove();
            trigger.removeAttribute('aria-describedby');
            document.removeEventListener('click', dismiss);
          }
        };
        setTimeout(() => document.addEventListener('click', dismiss), 0);
      }
    }
  }

  // ===========================================================================
  // INITIALIZATION
  // ===========================================================================

  function init() {
    // Attach click handlers to all stat definition triggers
    document.addEventListener('click', handleStatTriggerClick, true);

    // Handle sort buttons (basic URL state management)
    document.addEventListener('click', (event) => {
      const sortBtn = event.target.closest('.wcfb-sort-btn');
      if (!sortBtn) return;

      const th = sortBtn.closest('th');
      const sortId = th?.getAttribute('data-sort');
      if (!sortId) return;

      const currentSort = th.getAttribute('aria-sort');
      const newSort = currentSort === 'ascending' ? 'descending' : 'ascending';

      // Update URL fragment without jumping
      const url = new URL(window.location);
      url.hash = `#sort=${sortId}-${newSort}`;
      history.replaceState(null, '', url.toString());

      // Update visual state
      document.querySelectorAll('th[aria-sort]').forEach(el => {
        el.removeAttribute('aria-sort');
      });
      th.setAttribute('aria-sort', newSort);

      // Actual sorting would be handled by backend or additional JS
      // For static site, we'd need client-side sorting logic here
    });

    // Monitor horizontal scroll for scroll hint
    document.querySelectorAll('.wcfb-stats-wrap').forEach(wrap => {
      const updateScrollState = () => {
        const isScrolling = wrap.scrollLeft > 0;
        wrap.classList.toggle('wcfb-scrolling', isScrolling);
      };
      wrap.addEventListener('scroll', updateScrollState);
      updateScrollState();
    });
  }

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Export for potential external use
  window.CFBStatsDefinitions = {
    show: (statId) => {
      const isMobile = window.innerWidth < 768;
      if (isMobile) {
        const sheet = createBottomSheet(statId);
        if (sheet) {
          document.body.appendChild(sheet);
          sheet.offsetHeight;
          sheet.classList.add('wcfb-stats-bottom-sheet--open');
        }
      }
    },
    definitions: STAT_DEFINITIONS,
  };

})();
