# Anthropic UX Review Hook

This project now includes a small review script for getting a second-opinion critique on the player stats page from Anthropic's Messages API.

Official Anthropic references used for this hook:

- [Messages API](https://docs.anthropic.com/fr/api/messages)
- [Messages examples](https://docs.anthropic.com/en/api/messages-examples)
- [Models overview](https://docs.anthropic.com/en/docs/models-overview)
- [Vision guide](https://docs.anthropic.com/en/docs/build-with-claude/vision)

## Setup

Add your key to `.env`:

```bash
ANTHROPIC_API_KEY=your_key_here
```

## Typical usage

```bash
python scripts/anthropic_stats_page_review.py ^
  --html output/site/players/fernando-mendoza-2431.html ^
  --image tmp_home_desktop.png ^
  --focus "Current Season Production section on a college football player page"
```

The script will:

- send the relevant HTML excerpt
- optionally attach one or more screenshots
- ask for a concrete front-end and UX critique
- save the answer to `output/anthropic-stats-page-review.md`

## Notes

- The default model is `claude-sonnet-4-20250514`.
- Images are sent as base64 blocks, matching Anthropic's documented vision input format.
- The script trims the HTML payload so you do not accidentally ship the entire page source every time.
- This is intended as a critique tool, not a runtime dependency for the site.
