# Claude Cowork Prompt: CFB Fan-Intelligence Source Map

You are my senior data-products coworker helping pressure-test a college-football fan-intelligence product. The product is a Python + SQLite + static-site generator that publishes rankings and fan mood/magazine pages. I am a solo, mostly non-technical operator with ChatGPT Pro, Claude Max, and roughly $50/month incremental budget for data/infra. The core value proposition is defensible numbers: every published metric must be computed from identifiable sources or visibly tagged editorial/curated.

Your job is to brainstorm the best additional data sources beyond Reddit for understanding CFB and individual team fanbases across platforms, demographics, regions, and media ecosystems. Do not write code. Return a prioritized source strategy that can be implemented by a solo operator.

Current system context:

- Current facts/model data: CollegeFootballData + existing local SQLite tables.
- Current conversation data: Reddit submissions from r/CFB and some team subreddits, with Arctic Shift for historical backfill and Reddit official API planned for forward collection.
- Current issue: Reddit submissions are too narrow; comments help, but still skew toward Reddit demographics.
- Existing storage shape: `conversation_documents`, `conversation_document_targets`, `team_week_conversation_features`, `team_conversation_daily`, `fanbase_mood_weekly`, `rivalry_obsession_weekly`, `lexicon_weekly`.
- Publication rule: source/provenance must be row-level. No number can look computed unless it comes from a specific source, date window, and sample.
- Budget rule: assume no source above $25/month unless it is obviously worth replacing several weaker sources.
- Operator rule: avoid brittle scrapes that require daily manual babysitting.

Please evaluate sources in these categories:

- Official/cheap sports facts APIs: CollegeFootballData tiers, NCAA/ESPN/unofficial sports endpoints, TheSportsDB, odds APIs, prediction-market APIs.
- Fan conversation platforms: Reddit, YouTube comments, Bluesky, Mastodon, public Facebook/Instagram limitations, X/Twitter alternatives, Discord limitations, team forums/message boards, SB Nation/On3/247-style comments.
- News and media pulse: GDELT, Google News/RSS, school athletic sites, beat writers, local newspapers, press releases, podcasts/transcripts.
- Search/social trend proxies: Google Trends, YouTube search volume, Wikipedia pageviews, Link aggregators, newsletter/RSS ecosystems.
- Regional/demographic proxies: local news domains, alumni/community subreddits, city/state forums, school-specific communities.

For each promising source, give:

1. What signal it contributes that Reddit does not.
2. Whether it can support numeric publication, directional-only publication, or citation-only editorial use.
3. Cost estimate and whether it fits the $50/month budget.
4. Terms/licensing/retention risk.
5. Reliability risk.
6. Implementation difficulty for Python + SQLite.
7. Recommended cadence.
8. How to label provenance in the product.

Then recommend:

- The ideal source stack for the next 30 days.
- The ideal stack for the 2026 season kickoff.
- The “do not use yet” list and why.
- A simple source confidence tiering system.
- A minimum viable multi-platform collection plan for 20 high-interest teams.
- Any schema or provenance fields the existing system should add before collecting from more sources.

Be adversarial: call out sources that sound attractive but would create fake precision, demographic bias, legal risk, high maintenance, or numbers that cannot be defended.
