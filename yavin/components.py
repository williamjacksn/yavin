import flask
import htpy
import markupsafe
import yavin.versions


def _back_to_home() -> htpy.a:
    return _breadcrumb(flask.url_for("index"), "Home")


def _base(
    title: str = "Yavin",
    sign_in_block=None,
    breadcrumb=None,
    content=None,
    end_of_body=None,
) -> htpy.html:
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
                    htpy.div(".col")[breadcrumb or _breadcrumb(),],
                    htpy.div(".col")[sign_in_block or _sign_in(),],
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


def _breadcrumb(href="#", label="Yavin") -> htpy.a:
    icon_class = ".bi-house-fill" if label == "Yavin" else ".bi-chevron-left"
    return htpy.a(".btn.btn-outline-dark", href=href)[
        htpy.strong[
            htpy.i(icon_class),
            " ",
            label,
        ],
    ]


_debug_layout = [
    " ",
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
            htpy.hr,
            htpy.small(".text-body-secondary")[
                yavin.versions.app_version,
                flask.g.app_settings.get("debug_layout") == "true" and _debug_layout,
            ],
        ],
    ]


def _page_title(title: str) -> htpy.div:
    return htpy.div(".pt-3.row")[htpy.div(".col")[htpy.h1[title]]]


def _sign_in() -> htpy.a:
    return htpy.a(".btn.btn-primary.float-end", href=flask.url_for("sign_in"))[
        htpy.i(".bi-person-fill"),
        " Sign in",
    ]


def _user_menu(email: str, is_admin: bool) -> htpy.div:
    return htpy.div(".dropdown.float-end")[
        htpy.button(
            ".btn.btn-primary.dropdown-toggle", data_bs_toggle="dropdown", type="button"
        )[htpy.i(".bi-person-fill"),],
        htpy.div(".dropdown-menu.dropdown-menu-right")[
            htpy.h6(".dropdown-header")[email],
            is_admin
            and [
                htpy.a(".dropdown-item", href=flask.url_for("app_settings"))[
                    "App settings"
                ],
                htpy.a(".dropdown-item", href=flask.url_for("user_permissions"))[
                    "User permissions"
                ],
            ],
            htpy.a(".dropdown-item", href=flask.url_for("sign_out"))["Sign out"],
        ],
    ]


def app_settings() -> str:
    fs_expenses = htpy.fieldset[
        htpy.legend["Expenses"],
        htpy.div(".mb-3")[
            htpy.label(".form-label", for_="expenses_db")["Expenses database path"],
            htpy.input(
                "#expenses_db.form-control",
                name="expenses_db",
                type="text",
                value=flask.g.app_settings.get("expenses_db"),
            ),
        ],
    ]
    fs_smtp = htpy.fieldset[
        htpy.legend["SMTP settings"],
        htpy.div(".mb-3")[
            htpy.label(".form-label", for_="smtp_server")["SMTP server"],
            htpy.input(
                "#smtp_server.form-control",
                name="smtp_server",
                type="text",
                value=flask.g.app_settings.get("smtp_server"),
            ),
        ],
        htpy.div(".mb-3")[
            htpy.label(".form-label", for_="smtp_username")["SMTP username"],
            htpy.input(
                "#smtp_username.form-control",
                name="smtp_username",
                type="text",
                value=flask.g.app_settings.get("smtp_username"),
            ),
        ],
        htpy.div(".mb-3")[
            htpy.label(".form-label", for_="smtp_password")["SMTP password"],
            htpy.input(
                "#smtp_password.form-control",
                name="smtp_password",
                type="password",
                value=flask.g.app_settings.get("smtp_password"),
            ),
        ],
        htpy.div(".mb-3")[
            htpy.label(".form-label", for_="smtp_from_address")["SMTP from address"],
            htpy.input(
                "#smtp_from_address.form-control",
                name="smtp_from_address",
                type="text",
                value=flask.g.app_settings.get("smtp_from_address"),
            ),
        ],
    ]
    fs_other = htpy.fieldset[
        htpy.legend["Other settings"],
        htpy.div(".form-check.mb-3")[
            htpy.input(
                "#debug_layout.form-check-input",
                name="debug_layout",
                type="checkbox",
                checked=(flask.g.app_settings.get("debug_layout") == "true"),
            ),
            htpy.label(".form-check-label", for_="debug_layout")[
                "Enable debug layout hints"
            ],
        ],
    ]
    content = [
        _page_title("App settings"),
        htpy.div(".pt-3.row")[
            htpy.div(".col-12.col-sm-10.col-md-8.col-lg-7.col-xl-4")[
                htpy.form(action=flask.url_for("app_settings_update"), method="post")[
                    fs_expenses,
                    fs_smtp,
                    fs_other,
                    htpy.button(".btn.btn-primary", type="submit")["Save"],
                ]
            ]
        ],
    ]
    return signed_in(
        flask.g.email,
        flask.g.permissions,
        _back_to_home(),
        content,
        "Yavin / App settings",
    )


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


def index_signed_in(email: str, permissions: list[str], cards: list[dict]) -> str:
    card_nodes = []
    for card in cards:
        if card.get("visible"):
            card_nodes.append(
                htpy.div(".col", hx_get=card.get("url"), hx_trigger="load")
            )
    content = htpy.div(
        ".g-2.pt-3.row.row-cols-2.row-cols-md-3.row-cols-lg-4.row-cols-xl-5.row-cols-xxl-6"
    )[card_nodes]
    return signed_in(email, permissions, _breadcrumb(), content)


def index_signed_out() -> str:
    return htpy.render_node(_base())


def not_authorized(email: str, permissions: list[str]) -> str:
    content = htpy.div(".row")[
        htpy.div(".col")[
            htpy.h1["Not authorized"],
            htpy.p(".lead")["You are not authorized to view this page."],
        ]
    ]
    return signed_in(email, permissions, _back_to_home(), content)


def signed_in(
    email: str, permissions: list[str], breadcrumb=None, content=None, title=None
) -> str:
    is_admin = "admin" in permissions
    return htpy.render_node(
        _base(
            title,
            sign_in_block=_user_menu(email, is_admin),
            breadcrumb=breadcrumb,
            content=content,
        )
    )
