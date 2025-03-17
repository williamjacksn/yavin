import flask
import htpy
import markupsafe


def dashboard_card(
    card_title: str, card_href: str = None, card_text: str = None
) -> str:
    return htpy.render_node(
        htpy.div(".card.h-100")[
            htpy.div(".card-body")[
                htpy.h5(".card-title")[markupsafe.Markup(card_title)],
                card_href
                and htpy.a(
                    ".card-link.stretched-link.text-decoration-none.text-reset",
                    href=card_href,
                )[card_text],
            ]
        ]
    )


def dashboard_card_balances(text: str) -> str:
    return dashboard_card("Balances", flask.url_for("balances"), text)


def dashboard_card_billboard(latest: str) -> str:
    return dashboard_card("Billboard Hot 100 #1", flask.url_for("billboard"), latest)


def dashboard_card_captains_log() -> str:
    return dashboard_card("Captain&#x02bc;s log", flask.url_for("captains_log"), "Go")


def dashboard_card_electricity() -> str:
    return dashboard_card("Electricity", flask.url_for("electricity"), "Go")


def dashboard_card_expenses() -> str:
    return dashboard_card("Expenses", flask.url_for("expenses"), "Go")


def dashboard_card_jar() -> str:
    return dashboard_card("Jar", flask.url_for("jar"), "Go")


def dashboard_card_library() -> str:
    return dashboard_card("Library", flask.url_for("library"), "Go")


def dashboard_card_movie_night(next_pick: str) -> str:
    return dashboard_card(
        "Movie night", flask.url_for("movie_night"), f"Next pick: {next_pick}"
    )


def dashboard_card_phone() -> str:
    return dashboard_card("Phone usage", flask.url_for("phone"), "Go")


def dashboard_card_tithing() -> str:
    return dashboard_card("Tithing", flask.url_for("tithing"), "Go")


def dashboard_card_weight() -> str:
    return dashboard_card("Weight", flask.url_for("weight"), "Go")
