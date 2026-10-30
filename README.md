# Yavin

Personal web tools

## Playlist export

Read a CSV of songs (with `Song`, `Artist`, and `Album` columns) and write a new CSV that
adds a YouTube Music album link for each song.

```
uv run playlist -i playlist.csv -o out.csv
```

The input path defaults to `playlist.csv` and the output to `out.csv`, so a
bare `uv run playlist` works too.

## Tello balances

Collect Tello balances on another machine (for example, a home computer) and submit them
to Yavin:

```
uv run tello-submit --url https://yavin.example.com
```

The tool reads these environment variables, and prompts for any that are missing when
run in a terminal:

- `TELLO_USERNAME` and `TELLO_PASSWORD`: Tello account credentials
- `YAVIN_AUTH_PHRASE`: the `ADMIN_AUTH_PHRASE` configured on the Yavin server
- `YAVIN_URL`: the Yavin base URL, used when `--url` is not given

Run it once a day (with cron or Windows Task Scheduler) to keep the Tello page current.
Yavin sends a low-data email when any line has less than 10% of its data available.
