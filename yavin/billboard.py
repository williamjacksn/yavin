import collections
import logging

import httpx
import lxml.html

log = logging.getLogger(__name__)

Song = collections.namedtuple("Song", "artist title")


def fetch_number_one() -> Song:
    log.info("Fetching Billboard Hot 100 #1")
    url = "https://www.billboard.com/charts/hot-100/"
    resp = httpx.get(url)
    resp.raise_for_status()
    doc = lxml.html.document_fromstring(resp.content)

    title_el = doc.cssselect("li.o-chart-results-list__item h3")[0]
    title = str(title_el.text_content()).strip()

    title_parent = title_el.getparent()
    artist_el = title_parent.cssselect("span")[0]
    artist = str(artist_el.text_content()).strip()
    return Song(artist, title)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    log.info(fetch_number_one())


if __name__ == "__main__":
    main()
