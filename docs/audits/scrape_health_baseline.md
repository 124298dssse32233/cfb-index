# Scrape Health Baseline — 2026-04-23

Captured at the start of Autopilot v1. Every subsequent workstream must
improve (or at minimum not degrade) these numbers. The final audit (TASK 9.1)
diffs against this file.

## 200-word summary

The fan intelligence system shows mixed readiness. Of 169 active sources, Tier A (highest priority) has only 9 sources, indicating heavy reliance on mid-tier coverage. The scrape health over the past 30 days reveals 76 sources in error state (45%), 18 empty (11%), and 81 healthy (48%). Critical gaps exist in athletics and beat reporter sources—nearly all 19 athletics feeds and 14 beat reporters across major programs show errors with zero rows ingested. Conversely, Locked On podcasts dominate success metrics: 14 sources returning 500-row batches (7043 rows total). Campus feeds show spotty performance (7 of 14 ingesting data). Domain diversity is weak: Google News, Locked On, and podcast sources carry disproportionate weight. Positives: 21864 team-cohort cells tracked across 80 weeks; 41092 source observations logged; 1822 divergence records captured. Feed URL validation shows 60 healthy URLs and 1 error (97% healthy). The system is operational but source-dependent, with third-party feed infrastructure vulnerable. Athletics/beat reporter failure requires immediate investigation before Autopilot v1 launch.

## Raw output — scrape-health --since-days 30

```
source_id                    last_run        rows status  
----------------------------------------------------------
athletics_alabama            2026-04-23         0 error   
athletics_boise-state        2026-04-23         0 error   
athletics_byu                2026-04-23         0 error   
athletics_clemson            2026-04-23         0 error   
athletics_florida-state      2026-04-23         0 error   
athletics_georgia            2026-04-23         0 error   
athletics_kansas-state       2026-04-23         0 error   
athletics_lsu                2026-04-23         0 error   
athletics_memphis            2026-04-23         0 error   
athletics_miami              2026-04-23         0 error   
athletics_michigan           2026-04-23         0 error   
athletics_notre-dame         2026-04-23         0 error   
athletics_ohio-state         2026-04-23         0 error   
athletics_oregon             2026-04-23         0 error   
athletics_penn-state         2026-04-23         0 error   
athletics_tennessee          2026-04-23         0 error   
athletics_texas              2026-04-23         0 error   
athletics_texas-tech         2026-04-23         0 error   
athletics_tulane             2026-04-23         0 error   
beat_alabama_tuscaloosa_news 2026-04-23         0 error   
beat_boise-state_idaho_state 2026-04-23         0 error   
beat_byu_deseret_news_byu    2026-04-23         0 error   
beat_clemson_greenville_news 2026-04-23         0 error   
beat_florida-state_tallahass 2026-04-23         0 error   
beat_georgia_ajc_seth_emerso 2026-04-23         0 error   
beat_georgia_dawg_nation     2026-04-23         0 error   
beat_howard_washington_post_ 2026-04-23         0 error   
beat_jackson-state_clarion_l 2026-04-23         0 error   
beat_kansas-state_topeka_cap 2026-04-23         0 error   
beat_lsu_advocate_lsu        2026-04-23         0 error   
beat_memphis_commercial_appe 2026-04-23         0 error   
beat_miami_miami_herald_cane 2026-04-23         0 error   
beat_michigan_detroit_free_p 2026-04-23         0 error   
beat_ohio-state_dispatch_osu 2026-04-23         0 error   
beat_penn-state_centre_daily 2026-04-23         0 error   
beat_tennessee_knoxville_sen 2026-04-23         0 error   
beat_texas-tech_lubbock_aval 2026-04-23         0 error   
beat_texas_statesman_longhor 2026-04-23         0 error   
beat_tulane_advocate_tulane  2026-04-23         0 error   
campus_byu                   2026-04-23         0 error   
campus_florida-state         2026-04-23         0 error   
campus_lsu                   2026-04-23         0 error   
campus_memphis               2026-04-23         0 error   
campus_notre-dame            2026-04-23         0 error   
campus_tennessee             2026-04-23         0 error   
campus_texas-tech            2026-04-23         0 error   
google_news_alabama          2026-04-23         0 error   
google_news_boise-state      2026-04-23         0 error   
google_news_byu              2026-04-23         0 error   
google_news_clemson          2026-04-23         0 error   
google_news_florida-state    2026-04-23         0 error   
google_news_georgia          2026-04-23         0 error   
google_news_jackson-state    2026-04-23         0 error   
google_news_kansas-state     2026-04-23         0 error   
google_news_lsu              2026-04-23         0 error   
google_news_miami            2026-04-23         0 error   
google_news_michigan         2026-04-23         0 error   
google_news_ohio-state       2026-04-23         0 error   
google_news_oregon           2026-04-23         0 error   
google_news_penn-state       2026-04-23         0 error   
google_news_tennessee        2026-04-23         0 error   
google_news_texas            2026-04-23         0 error   
google_news_texas-tech       2026-04-23         0 error   
podcast_saturday_down_south_ 2026-04-23         0 error   
predict_thin                 2026-04-23         0 error   
radio_radio_birmingham_wjox  2026-04-23         0 error   
radio_radio_dallas_1053      2026-04-23         0 error   
radio_radio_knoxville_wnml   2026-04-23         0 error   
substack_football_brainiacs  2026-04-23         0 error   
substack_good_call           2026-04-23         0 error   
substack_max_olson           2026-04-23         0 error   
substack_recruiting_scoops   2026-04-23         0 error   
substack_swindle_stats       2026-04-23         0 error   
substack_the_athletic_cfb    2026-04-23         0 error   
substack_the_solid_verbal    2026-04-23         0 error   
tiktok_observed              2026-04-23         0 error   
athletics_jackson-state      2026-04-23         0 empty   
bluesky_curated              2026-04-23         0 empty   
bluesky_feeds                2026-04-23         0 empty   
campus_alabama               2026-04-23         0 empty   
campus_boise-state           2026-04-23         0 empty   
campus_clemson               2026-04-23         0 empty   
campus_georgia               2026-04-23         0 empty   
campus_howard                2026-04-23         0 empty   
campus_jackson-state         2026-04-23         0 empty   
campus_kansas-state          2026-04-23         0 empty   
campus_miami                 2026-04-23         0 empty   
campus_ohio-state            2026-04-23         0 empty   
campus_penn-state            2026-04-23         0 empty   
campus_texas                 2026-04-23         0 empty   
kalshi                       2026-04-23         0 empty   
seatgeek                     2026-04-23         0 empty   
spotify_charts               2026-04-23         0 empty   
wiki_pv                      2026-04-24         0 empty   
beat_articles                2026-04-23         0 skipped 
board_quotes                 2026-04-23         0 skipped 
press_releases               2026-04-23         0 skipped 
athletics_howard             2026-04-23         1 ok      
beat_alabama_al_com_alabama  2026-04-23         0 ok      
beat_alabama_roll_bama_roll  2026-04-23         0 ok      
beat_clemson_shakin_the_sout 2026-04-23         0 ok      
beat_florida-state_tomahawk_ 2026-04-23         0 ok      
beat_jackson-state_hbcu_game 2026-04-23         0 ok      
beat_kansas-state_bring_on_t 2026-04-23         0 ok      
beat_memphis_underdog_dynast 2026-04-23         0 ok      
beat_michigan_maize_n_brew   2026-04-23         0 ok      
beat_ohio-state_land_grant_h 2026-04-23         0 ok      
beat_oregon_oregonian_ducks  2026-04-23         0 ok      
beat_tennessee_rocky_top_ins 2026-04-23         0 ok      
beat_texas-tech_wreck_em_red 2026-04-23         0 ok      
bluesky_firehose             2026-04-23         0 ok      
bluesky_starterpack          2026-04-23         0 ok      
board_247_free               2026-04-23         0 ok      
campus_michigan              2026-04-23         2 ok      
campus_oregon                2026-04-23        10 ok      
campus_tulane                2026-04-23         1 ok      
cfbd                         2026-04-23         0 ok      
facebook_alumni_glance       2026-04-23         0 ok      
finebaum_rss                 2026-04-23         0 ok      
gdelt_tone                   2026-04-23         0 ok      
gdelt_volume                 2026-04-23         8 ok      
google_news_howard           2026-04-23        20 ok      
google_news_memphis          2026-04-23         5 ok      
google_news_notre-dame       2026-04-23       102 ok      
google_news_tulane           2026-04-23         9 ok      
google_trends_dma            2026-04-23         0 ok      
locked_on_alabama            2026-04-23       500 ok      
locked_on_byu                2026-04-23       500 ok      
locked_on_florida-state      2026-04-23       500 ok      
locked_on_georgia            2026-04-23       500 ok      
locked_on_kansas-state       2026-04-23       427 ok      
locked_on_lsu                2026-04-23       500 ok      
locked_on_miami              2026-04-23       500 ok      
locked_on_michigan           2026-04-23       500 ok      
locked_on_notre-dame         2026-04-23       500 ok      
locked_on_ohio-state         2026-04-23       500 ok      
locked_on_oregon             2026-04-23       500 ok      
locked_on_penn-state         2026-04-23       500 ok      
locked_on_tennessee          2026-04-23       500 ok      
locked_on_texas              2026-04-23       500 ok      
podcast_finebaum_rss         2026-04-23         0 ok      
podcast_locked_on_alabama    2026-04-23         0 ok      
podcast_locked_on_buckeyes   2026-04-23         0 ok      
podcast_locked_on_college_fo 2026-04-23         0 ok      
podcast_locked_on_ducks      2026-04-23         0 ok      
podcast_locked_on_georgia    2026-04-23         0 ok      
podcast_locked_on_lsu        2026-04-23         0 ok      
podcast_locked_on_wolverines 2026-04-23         0 ok      
podcast_split_zone_duo       2026-04-23         0 ok      
podcast_the_audible          2026-04-23         0 ok      
podcast_the_solid_verbal     2026-04-23         0 ok      
polymarket                   2026-04-23        10 ok      
radio_radio_ann_arbor_971    2026-04-23         0 ok      
radio_radio_atlanta_929      2026-04-23         0 ok      
radio_radio_baton_rouge_wbrp 2026-04-23         0 ok      
radio_radio_columbus_9710    2026-04-23         0 ok      
radio_radio_jackson_wjdx     2026-04-23         0 ok      
radio_radio_portland_1080    2026-04-23         0 ok      
radio_radio_salt_lake_ksl    2026-04-23         0 ok      
reddit_alumni                2026-04-23         0 ok      
reddit_cfb                   2026-04-23         0 ok      
reddit_city                  2026-04-23         0 ok      
reddit_team                  2026-04-23         0 ok      
substack_bud_elliott         2026-04-23         0 ok      
substack_extra_points        2026-04-23         0 ok      
substack_go_long             2026-04-23         0 ok      
substack_hbcu_gameday        2026-04-23         0 ok      
substack_on3_recruits        2026-04-23         0 ok      
substack_saturday_road       2026-04-23         0 ok      
substack_saturday_tradition  2026-04-23         0 ok      
substack_split_zone_duo      2026-04-23         0 ok      
twitch_chat                  2026-04-23         0 ok      
wiki_edits                   2026-04-24         2 ok      
youtube_comments_nat         2026-04-23         0 ok      
youtube_comments_team        2026-04-23         0 ok      
youtube_meta                 2026-04-23      1147 ok
```

## Raw output — fanintel-status

```
================================================================
Fan Intelligence – operational status
================================================================

source_registry: 204 fanintel rows (169 active)
  tier A: 9
  tier B: 175
  tier C: 4
  tier D: 16

priority_teams: 21 teams (0 flagged needs_research)

scrape_health (last 7 days):
  empty: 18
  error: 76
  ok: 81
  skipped: 3

team_cohort_week: 21864 cells across 123 teams – 80 weeks

source_observations: 41092 rows from 5 distinct source_id's

conversation_documents: 21188 rows (9426 with new-schema source_id populated)

team_cohort_divergence_week: 1822 rows (46 with qualifying divergence_score)

================================================================
```

## Raw output — validate-feed-urls

```
Validating source_registry terms_url entries...
  ok=60 error=1 skipped=3 total=64
  See `python manage.py scrape-health` for error details.
```
