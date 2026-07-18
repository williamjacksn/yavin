"""Export a Spotify playlist to CSV using
https://www.chosic.com/spotify-playlist-exporter/ then use this tool to look up the
YouTube Music album page for each song in the playlist."""

import argparse
import collections
import csv
import logging
import pathlib

import notch
from ytmusicapi import YTMusic

notch.configure()
log = logging.getLogger(__name__)

Song = collections.namedtuple("Song", "title artist album")


def read_songs(path: pathlib.Path) -> list[Song]:
    """Read songs from a CSV with Song, Artist, and Album columns."""
    songs: list[Song] = []
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = (row.get("Song") or "").strip()
            if not title:
                continue
            songs.append(
                Song(
                    title=title,
                    artist=(row.get("Artist") or "").strip(),
                    album=(row.get("Album") or "").strip(),
                )
            )
    return songs


def youtube_music_album_url(
    ytmusic: YTMusic, album: str, artist: str, cache: dict[tuple[str, str], str]
) -> str:
    """Return the YouTube Music album page URL, or "" if nothing matches."""
    log.debug(f"Current cache size: {len(cache)}")
    key = (album, artist)
    if key in cache:
        return cache[key]
    result = ""
    if album:
        # Use only the primary artist; a long comma-joined list of features makes
        # the album search too noisy to match.
        primary_artist = artist.split(",")[0].strip()
        query = f"{album} {primary_artist}".strip()
        hits = ytmusic.search(query, filter="albums")
        if hits and hits[0].get("browseId"):
            result = f"https://music.youtube.com/browse/{hits[0]['browseId']}"
    cache[key] = result
    return result


def write_csv(path: pathlib.Path, rows: list[tuple[Song, str]]) -> None:
    with path.open(mode="w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Song", "Artist", "Album", "YouTube Music Link"])
        for song, link in rows:
            writer.writerow([song.title, song.artist, song.album, link])


class Args:
    input: pathlib.Path
    output: pathlib.Path


def parse_args() -> Args:
    parser = argparse.ArgumentParser(
        description="Add YouTube Music album links to a CSV of songs."
    )
    parser.add_argument(
        "-i",
        "--input",
        type=pathlib.Path,
        default=pathlib.Path("playlist.csv"),
        help="Input CSV path (default: playlist.csv)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=pathlib.Path,
        default=pathlib.Path("out.csv"),
        help="Output CSV path (default: out.csv)",
    )
    return parser.parse_args(namespace=Args())


def main() -> None:
    args = parse_args()

    songs = read_songs(args.input)
    log.info("Read %d songs; looking up YouTube Music albums", len(songs))

    ytmusic = YTMusic()
    cache: dict[tuple[str, str], str] = {}
    rows = [
        (song, youtube_music_album_url(ytmusic, song.album, song.artist, cache))
        for song in songs
    ]

    write_csv(args.output, rows)
    log.info("Wrote %d songs to %s", len(rows), args.output)


if __name__ == "__main__":
    main()
