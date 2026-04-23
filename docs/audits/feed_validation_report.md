# Fan Intelligence — Feed URL Validation Report

Generated: 2026-04-23. Generator: python manage.py validate-feed-urls.

## Summary

- **error**: 47
- **ok**: 39
- **skipped**: 3

## Errored sources - triage needed

| source_id | terms_url | error |
|---|---|---|
| beat_alabama_tuscaloosa_news_cecil | https://www.tuscaloosanews.com/rss | HTTP 403 |
| beat_boise-state_idaho_statesman | https://www.idahostatesman.com/sports/college/mountain-west/boise-state-university/rss | TimeoutError: The read operation timed out |
| beat_byu_deseret_news_byu | https://www.deseret.com/feeds/byu/ | HTTP 404 |
| beat_clemson_greenville_news | https://www.greenvilleonline.com/feeds/sports/ | HTTP 403 |
| beat_florida-state_tallahassee_democrat | https://www.tallahassee.com/feeds/sports/ | HTTP 403 |
| beat_georgia_ajc_seth_emerson | https://www.ajc.com/arc/outboundfeeds/rss/category/sports/uga/ | HTTP 404 |
| beat_georgia_dawg_nation | https://www.dawgnation.com/feed | HTTP 404 |
| beat_howard_washington_post_dc_colleges | https://www.washingtonpost.com/wp-srv/rss/metro/colleges.xml | TimeoutError: The read operation timed out |
| beat_jackson-state_clarion_ledger | https://www.clarionledger.com/feeds/sports/ | HTTP 403 |
| beat_kansas-state_topeka_capital | https://www.cjonline.com/feeds/sports/ | HTTP 403 |
| beat_lsu_advocate_lsu | https://www.theadvocate.com/tncms/rss/?t=article&c=sports/lsu/football | HTTP 500 |
| beat_memphis_commercial_appeal | https://www.commercialappeal.com/feeds/sports/ | HTTP 403 |
| beat_miami_miami_herald_canes | https://www.miamiherald.com/sports/college/acc/university-of-miami/rss | TimeoutError: The read operation timed out |
| beat_michigan_detroit_free_press_um | https://www.freep.com/feeds/sports/michigan/ | HTTP 403 |
| beat_ohio-state_dispatch_osu | https://www.dispatch.com/arc/outboundfeeds/rss/category/sports/ohio-state/ | HTTP 403 |
| beat_penn-state_centre_daily_times | https://www.centredaily.com/sports/college/penn-state-university/rss | TimeoutError: The read operation timed out |
| beat_tennessee_knoxville_sentinel_football | https://www.knoxnews.com/feeds/sports/ | HTTP 403 |
| beat_texas-tech_lubbock_avalanche | https://www.lubbockonline.com/feeds/sports/ | HTTP 403 |
| beat_texas_statesman_longhorns | https://www.statesman.com/arc/outboundfeeds/rss/category/sports/longhorns/ | HTTP 404 |
| beat_tulane_advocate_tulane | https://www.theadvocate.com/tncms/rss/?t=article&c=sports/tulane | HTTP 500 |
| kalshi | https://kalshi.com/terms | HTTP 429 |
| podcast_finebaum_rss | https://rss.art19.com/paul-finebaum-show | HTTP 404 |
| podcast_locked_on_alabama | https://feeds.megaphone.fm/lockedonalabama | HTTP 404 |
| podcast_locked_on_buckeyes | https://feeds.megaphone.fm/lockedonbuckeyes | HTTP 404 |
| podcast_locked_on_college_football | https://feeds.megaphone.fm/lockedoncfb | HTTP 404 |
| podcast_locked_on_ducks | https://feeds.megaphone.fm/lockedonducks | HTTP 404 |
| podcast_locked_on_georgia | https://feeds.megaphone.fm/lockedongeorgia | HTTP 404 |
| podcast_locked_on_lsu | https://feeds.megaphone.fm/lockedonlsu | HTTP 404 |
| podcast_locked_on_wolverines | https://feeds.megaphone.fm/lockedonwolverines | HTTP 404 |
| podcast_saturday_down_south_podcast | https://feeds.megaphone.fm/sdsnetwork | HTTP 404 |
| podcast_split_zone_duo | https://feeds.megaphone.fm/VMP5705694282 | HTTP 404 |
| podcast_the_audible | https://feeds.simplecast.com/k6Opj0Mx | HTTP 404 |
| podcast_the_solid_verbal | https://feeds.simplecast.com/wkp4yYBk | HTTP 404 |
| predict_thin | https://kalshi.com/terms | HTTP 429 |
| radio_radio_birmingham_wjox | https://omny.fm/shows/the-roundtable/playlists/podcast.rss | HTTP 404 |
| radio_radio_dallas_1053 | https://www.thefan1053.com/feed | URLError: [Errno 11001] getaddrinfo failed |
| radio_radio_knoxville_wnml | https://www.sportsradiownml.com/feed | URLError: timed out |
| seatgeek | https://seatgeek.com/terms | HTTP 403 |
| substack_extra_points | https://www.extrapointsmb.com/feed | HTTP 404 |
| substack_football_brainiacs | https://footballbrainiacs.substack.com/feed | HTTP 404 |
| substack_good_call | https://goodcallnewsletter.substack.com/feed | HTTP 404 |
| substack_max_olson | https://theathletic.com/author/max-olson/feed/ | HTTP 404 |
| substack_recruiting_scoops | https://recruitingscoops.substack.com/feed | HTTP 404 |
| substack_swindle_stats | https://swindlestats.substack.com/feed | HTTP 404 |
| substack_the_athletic_cfb | https://theathletic.com/college-football/feed/ | HTTP 404 |
| substack_the_solid_verbal | https://www.thesolidverbal.com/feed | URLError: timed out |
| tiktok_observed | https://www.tiktok.com/legal/terms-of-service | TimeoutError: The read operation timed out |

## Next steps

1. For each error row, either update the feed URL in the source seed YAML or mark the source inactive in priority_teams / the seed file.
2. For needs-auth errors (kalshi, seatgeek) the URL itself is fine - the validator just cannot authenticate. These will work once the adapter runs with credentials.
3. Locked On podcast feed URLs were guessed (megaphone.fm/lockedon*) - correct URLs need confirming against lockedonpodcasts.com show pages.
4. Beat-writer feed URLs guessed from outlet RSS patterns - many outlets have moved to arc-outboundfeeds or removed RSS entirely; confirm per outlet.
5. Re-run python manage.py validate-feed-urls after updates; scrape_health auto-upserts.