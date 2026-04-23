# Player Honors Import

Use the template at `docs/player_honors_template.csv` and import it with:

```bash
python manage.py import-player-honors --csv docs/player_honors_template.csv --source-name manual
```

Recommended `honor_scope` values:

- `all_america`
- `all_conference`
- `weekly_honor`
- `conference_award`
- `national_award`
- `watch_list`
- `postseason_trophy`

Matching priority:

1. `player_id` if provided
2. `cfbd_player_id`
3. `cfbd_recruit_id`
4. exact `player_name`

Notes:

- Use `week=0` for season-end honors.
- Set `consensus_flag=1` and `unanimous_flag=1` when applicable.
- `selector` should hold the awarding body, such as `Associated Press`, `Walter Camp`, or `SEC`.
