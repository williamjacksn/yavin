import flask
import htpy
import markupsafe


def _base(title: str = "Yavin", content=None, end_of_body=None) -> htpy.html:
    return htpy.html(lang="en")[
        htpy.head[
            htpy.meta(charset="utf-8"),
            htpy.meta(
                content="width=device-width, initial-scale=1, shrink-to-fit=no",
                name="viewport",
            ),
            htpy.title[title],
            htpy.link(
                href=flask.url_for("static", filename="bootstrap-5.3.3.css"),
                rel="stylesheet",
            ),
            htpy.link(
                href=flask.url_for("static", filename="bootstrap-icons-1.11.3.css"),
                rel="stylesheet",
            ),
        ],
        htpy.body[
            htpy.div(".container-fluid")[
                htpy.div(".pt-3.row")[
                    htpy.div(".col")[_breadcrumb(),],
                    htpy.div(".col")[_sign_in(),],
                ],
                content,
                _footer(),
            ],
            htpy.script(
                src=flask.url_for("static", filename="bootstrap-5.3.3.bundle.js")
            ),
            htpy.script(src=flask.url_for("static", filename="htmx-2.0.4.js")),
            htpy.script(src=flask.url_for("static", filename="data-href-clickable.js")),
            end_of_body,
        ],
    ]


def _breadcrumb() -> htpy.a:
    return htpy.a(".btn.btn-outline-dark", href="#")[
        htpy.strong[
            htpy.i(".bi-house-fill"),
            " Yavin",
        ],
    ]


def _debug_layout() -> list[htpy.span]:
    return [
        htpy.span(".d-inline.d-sm-none")["xs"],
        htpy.span(".d-none.d-sm-inline.d-md-none")["sm"],
        htpy.span(".d-none.d-md-inline.d-lg-none")["md"],
        htpy.span(".d-none.d-lg-inline.d-xl-none")["lg"],
        htpy.span(".d-none.d-xl-inline.d-xxl-none")["xl"],
        htpy.span(".d-none.d-xxl-inline")["xxl"],
    ]


def _footer() -> htpy.div:
    return htpy.div(".pb-2.pt-3.row")[
        htpy.div(".col")[
            htpy.hr(".border-light"),
            htpy.small(".text-body-secondary")[
                flask.g.version,
                _debug_layout(),
            ],
        ],
    ]


def _sign_in() -> htpy.a:
    return htpy.a(".btn.btn-primary.float-end", href=flask.url_for("sign_in"))[
        htpy.i(".bi-person-fill"),
        " Sign in",
    ]


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


def index() -> str:
    return htpy.render_node(_base())
