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
