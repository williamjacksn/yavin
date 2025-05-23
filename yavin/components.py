import decimal
import flask
import htpy
import logging
import markupsafe
import yavin.util
import yavin.versions as v

log = logging.getLogger(__name__)


def _back_to_balances() -> htpy.a:
    return _breadcrumb(flask.url_for("balances"), "Balances")


def _back_to_home() -> htpy.a:
    return _breadcrumb(flask.url_for("index"), "Home")


def _back_to_library() -> htpy.a:
    return _breadcrumb(flask.url_for("library"), "Library")


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
            htpy.title[markupsafe.Markup(title)],
            htpy.link(
                href=flask.url_for("static", filename=f"bootstrap-{v.bs}.css"),
                rel="stylesheet",
            ),
            htpy.link(
                href=flask.url_for("static", filename=f"bootstrap-icons-{v.bi}.css"),
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
                src=flask.url_for("static", filename=f"bootstrap-{v.bs}.bundle.js")
            ),
            htpy.script(src=flask.url_for("static", filename=f"htmx-{v.hx}.js")),
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
                v.app_version,
                flask.g.app_settings.get("debug_layout") == "true" and _debug_layout,
            ],
        ],
    ]


def _page_title(title: str) -> htpy.div:
    return htpy.div(".pt-3.row")[htpy.div(".col")[htpy.h1[markupsafe.Markup(title)]]]


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


def balances() -> str:
    rows = []
    for a in flask.g.accounts:
        rows.append(
            htpy.tr(
                data_href=flask.url_for(
                    "balances_detail", account_id=a.get("account_id")
                ),
                role="button",
            )[
                htpy.td[a.get("account_name")],
                htpy.td(".text-end")[f"{a.get('account_balance'):,.2f}"],
            ]
        )
    content = [
        _page_title("Balances"),
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.table(".d-block.table.table-striped")[
                    htpy.thead[
                        htpy.tr[htpy.th["Account"], htpy.th(".text-end")["Balance"]]
                    ],
                    htpy.tbody[rows],
                ]
            ]
        ],
    ]
    return signed_in(
        flask.g.email,
        flask.g.permissions,
        _back_to_home(),
        content,
        "Yavin / Balances",
    )


def balances_detail() -> str:
    rows = []
    for t in flask.g.transactions:
        if t.get("tx_id"):
            badge_class = (
                "text-bg-success" if t.get("tx_value") >= 0 else "text-bg-danger"
            )
            rows.append(
                htpy.tr[
                    htpy.td[
                        htpy.span(".badge.text-bg-secondary")[
                            t.get("tx_date").isoformat()
                        ],
                        htpy.br,
                        t.get("tx_description"),
                    ],
                    htpy.td(".text-end")[
                        htpy.span(f".badge.{badge_class}")[
                            f"$ {abs(t.get('tx_value')):,.2f}"
                        ]
                    ],
                ]
            )
    modal_body_add_tx = htpy.div(".modal-body")[
        htpy.form(
            "#form-add-tx",
            action=flask.url_for("balances_add_tx"),
            method="post",
        )[
            htpy.input(
                name="account-id",
                type="hidden",
                value=str(flask.g.account_id),
            ),
            htpy.div(".mb-3")[
                htpy.label(".form-label", for_="tx-date")["Date"],
                htpy.input(
                    "#tx-date.form-control",
                    name="tx-date",
                    required=True,
                    type="date",
                    value=yavin.util.today().isoformat(),
                ),
            ],
            htpy.div(".mb-3")[
                htpy.label(".form-label", for_="tx-description")["Description"],
                htpy.input(
                    "#tx-description.form-control",
                    name="tx-description",
                    required=True,
                    type="text",
                ),
            ],
            htpy.div(".mb-3")[
                htpy.label(".form-label", for_="tx-value")["Amount"],
                htpy.input(
                    "#tx-value.form-control",
                    name="tx-value",
                    required=True,
                    step="0.01",
                    type="number",
                ),
            ],
        ]
    ]
    content = [
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.h1[flask.g.account_name],
                htpy.p["Current balance: $ ", f"{flask.g.account_balance:,.2f}"],
            ]
        ],
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.a(
                    ".btn.btn-success",
                    data_bs_target="#modal-add-tx",
                    data_bs_toggle="modal",
                )["Add transaction"]
            ]
        ],
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.table(".d-block.table.table-striped")[htpy.tbody[rows]]
            ]
        ],
        htpy.div("#modal-add-tx.modal")[
            htpy.div(".modal-dialog")[
                htpy.div(".modal-content")[
                    htpy.div(".modal-header")[
                        htpy.h5(".modal-title")["Add a transaction"]
                    ],
                    modal_body_add_tx,
                    htpy.div(".justify-content-between.modal-footer")[
                        htpy.button(".btn.btn-secondary", data_bs_dismiss="modal")[
                            "Cancel"
                        ],
                        htpy.button(".btn.btn-success", form="form-add-tx")[
                            "Add transaction"
                        ],
                    ],
                ]
            ]
        ],
    ]
    return signed_in(
        flask.g.email,
        flask.g.permissions,
        _back_to_balances(),
        content,
        f"Yavin / Balances / {flask.g.get('account_name')}",
    )


def billboard() -> str:
    content = [
        _page_title("Billboard Hot 100 #1"),
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.p[
                    htpy.strong[flask.g.latest.get("title")],
                    " by ",
                    flask.g.latest.get("artist"),
                ],
                htpy.p[
                    "Last fetched: ",
                    yavin.util.clean_datetime(flask.g.latest.get("fetched_at")),
                    " UTC",
                ],
            ]
        ],
    ]
    return signed_in(
        flask.g.email,
        flask.g.permissions,
        _back_to_home(),
        content,
        "Yavin / Billboard Hot 100 #1",
    )


def captains_log() -> str:
    tbody = htpy.tbody[
        (
            htpy.tr[
                htpy.td(".text-nowrap")[
                    yavin.util.clean_datetime(record.get("log_timestamp")),
                    " UTC",
                ],
                htpy.td[record.get("log_text")],
                htpy.td(".text-nowrap")[
                    htpy.button(
                        ".btn.btn-primary.btn-sm.me-1",
                        data_bs_target="#modal-edit",
                        data_bs_toggle="modal",
                        hx_post=flask.url_for("captains_log_modal_edit"),
                        hx_target="#modal-edit-dialog",
                        name="log-id",
                        value=str(record.get("id")),
                    )[htpy.i(".bi-pencil-fill")],
                    htpy.button(
                        ".btn.btn-danger.btn-sm",
                        data_bs_target="#modal-delete",
                        data_bs_toggle="modal",
                        hx_post=flask.url_for("captains_log_modal_delete"),
                        hx_target="#modal-delete-dialog",
                        name="log-id",
                        value=str(record.get("id")),
                    )[htpy.i(".bi-trash-fill")],
                ],
            ]
            for record in flask.g.records
        )
    ]
    content = [
        _page_title("Captain&#x02bc;s log"),
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.table(".d-block.table")[
                    htpy.thead[
                        htpy.tr[
                            htpy.th["Log date"], htpy.th["Log text"], htpy.th["Actions"]
                        ]
                    ],
                    tbody,
                ]
            ]
        ],
        htpy.div("#modal-edit.modal")[htpy.div("#modal-edit-dialog.modal-dialog")],
        htpy.div("#modal-delete.modal")[htpy.div("#modal-delete-dialog.modal-dialog")],
    ]
    return signed_in(
        flask.g.email,
        flask.g.permissions,
        _back_to_home(),
        content,
        "Yavin / Captain&#x02bc;s log",
    )


def captains_log_modal_delete(log_id: str) -> str:
    content = htpy.div(".modal-content")[
        htpy.div(".modal-header")[
            htpy.h5(".modal-title")["Delete this log"],
            htpy.button(".btn-close", data_bs_dismiss="modal", type="button"),
        ],
        htpy.div(".modal-body")["Are you sure you want to delete this log entry?"],
        htpy.div(".justify-content-between.modal-footer")[
            htpy.button(".btn.btn-secondary", data_bs_dismiss="modal", type="button")[
                "Cancel"
            ],
            htpy.form(action=flask.url_for("captains_log_delete"), method="post")[
                htpy.input(name="id", type="hidden", value=log_id),
                htpy.button(".btn.btn-danger", type="submit")["Delete"],
            ],
        ],
    ]
    return str(content)


def captains_log_modal_edit(log_entry: dict) -> str:
    content = htpy.div(".modal-content")[
        htpy.div(".modal-header")[
            htpy.h5(".modal-title")[
                yavin.util.clean_datetime(log_entry.get("log_timestamp")), " UTC"
            ],
            htpy.button(".btn-close", data_bs_dismiss="modal", type="button"),
        ],
        htpy.div(".modal-body")[
            htpy.form(
                "#form-edit",
                action=flask.url_for("captains_log_update"),
                method="post",
            )[
                htpy.input(name="id", type="hidden", value=str(log_entry.get("id"))),
                htpy.div(".mb-3")[
                    htpy.label(".form-label", for_="log-text"),
                    htpy.textarea("#log-text.form-control", name="log_text", rows=5)[
                        log_entry.get("log_text")
                    ],
                ],
            ],
        ],
        htpy.div(".justify-content-between.modal-footer")[
            htpy.button(".btn.btn-secondary", data_bs_dismiss="modal", type="button")[
                "Cancel"
            ],
            htpy.button(".btn.btn-success", form="form-edit", type="submit")["Save"],
        ],
    ]
    return str(content)


def dashboard_card(
    card_title: str, card_href: str = None, card_text: str = None
) -> str:
    content = htpy.div(".card.h-100")[
        htpy.div(".card-body")[
            htpy.h5(".card-title")[markupsafe.Markup(card_title)],
            card_href
            and htpy.a(
                ".card-link.stretched-link.text-decoration-none.text-reset",
                href=card_href,
            )[card_text],
        ]
    ]
    return str(content)


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


def dashboard_card_jar(days_since_last: int) -> str:
    plural = "" if days_since_last == 1 else "s"
    card_text = f"{days_since_last} day{plural} ago"
    return dashboard_card("Jar", flask.url_for("jar"), card_text)


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


def dashboard_card_weight(text: str) -> str:
    return dashboard_card("Weight", flask.url_for("weight"), text)


def electricity() -> str:
    rows = []
    for r in flask.g.records:
        rows.append(
            htpy.tr[
                htpy.td[r.get("bill_date").isoformat()],
                htpy.td(".text-end")[r.get("kwh")],
                htpy.td(".text-end")[int(r.get("avg_12_months"))],
                htpy.td(".text-end")[f"$ {r.get('charge'):,.2f}"],
                htpy.td(".text-end")[f"$ {r.get('bill'):,.2f}"],
            ]
        )
    content = [
        _page_title("Electricity"),
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.form(action=flask.url_for("electricity_add"), method="post")[
                    htpy.div(".g-1.row")[
                        htpy.div(".col-auto")[
                            htpy.input(
                                ".form-control",
                                aria_label="When",
                                name="bill_date",
                                required=True,
                                type="date",
                            )
                        ],
                        htpy.div(".col-auto")[
                            htpy.input(
                                ".form-control",
                                aria_label="kWh",
                                min=0,
                                name="kwh",
                                placeholder="kWh",
                                required=True,
                                step=1,
                                type="number",
                            )
                        ],
                        htpy.div(".col-auto")[
                            htpy.div(".input-group")[
                                htpy.span(".input-group-text")["$"],
                                htpy.input(
                                    ".form-control",
                                    aria_label="Charge",
                                    min=0,
                                    name="charge",
                                    placeholder="Charge",
                                    required=True,
                                    step="0.01",
                                    type="number",
                                ),
                            ]
                        ],
                        htpy.div(".col-auto")[
                            htpy.div(".input-group")[
                                htpy.span(".input-group-text")["$"],
                                htpy.input(
                                    ".form-control",
                                    aria_label="Bill",
                                    min=0,
                                    name="bill",
                                    placeholder="Bill",
                                    required=True,
                                    step="0.01",
                                    type="number",
                                ),
                            ]
                        ],
                        htpy.div(".col-auto")[
                            htpy.button(".btn.btn-success", type="submit")["Add"]
                        ],
                    ]
                ]
            ]
        ],
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.table(".d-block.table")[
                    htpy.thead[
                        htpy.tr[
                            htpy.th["Date"],
                            htpy.th(".text-end")["kWh"],
                            htpy.th(".text-end")["12 month avg"],
                            htpy.th(".text-end")["Charge"],
                            htpy.th(".text-end")["Bill"],
                        ]
                    ],
                    htpy.tbody[rows],
                ]
            ]
        ],
    ]
    return signed_in(
        flask.g.email,
        flask.g.permissions,
        _back_to_home(),
        content,
        "Yavin / Electricity",
    )


def email_billboard(song_title: str, song_artist: str) -> str:
    content = htpy.html(lang="en")[
        htpy.body[
            htpy.p["Hello,"],
            htpy.p["There is a new Billboard Hot 100 #1 song!"],
            htpy.p[htpy.strong[song_title], " by ", song_artist],
            htpy.p["(This is an automated message.)"],
        ]
    ]
    return str(content)


def email_library_item_due(due_books: list[dict]) -> str:
    content = htpy.html(lang="en")[
        htpy.body[
            htpy.p["Hello,"],
            htpy.p[
                "The following items are due (or possibly overdue) at the library today."
            ],
            htpy.ul[
                (
                    htpy.li[
                        htpy.em[b.get("title")],
                        " (",
                        b.get("medium"),
                        ") is due on ",
                        b.get("due").isoformat(),
                        " (",
                        b.get("account_name"),
                        ")",
                    ]
                    for b in due_books
                )
            ],
            htpy.p["(This is an automated message.)"],
        ]
    ]
    return str(content)


def expenses() -> str:
    expense_rows = []
    for e in flask.g.expenses:
        expense_rows.append(
            htpy.tr[
                htpy.td[
                    htpy.div(".g-1.justify-content-between.row")[
                        htpy.div(".col-auto")[
                            e["description"],
                            htpy.br,
                            e["memo"] and htpy.small[e["memo"]],
                        ],
                        htpy.div(".col-auto.text-end")[
                            htpy.strong[f"$ {e['amount']:,.2f}"]
                        ],
                    ],
                    htpy.div(".g-1.justify-content-between.row")[
                        htpy.div(".col-auto")[
                            htpy.span(".badge.bg-primary")[e["account"][13:]]
                        ],
                        htpy.div(".col-auto.text-body-secondary.text-end")[
                            e["post_date"][:10]
                        ],
                    ],
                ]
            ]
        )
    content = [
        _page_title("Expenses"),
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.form[
                    htpy.div(".g-1.row")[
                        htpy.div(".col-auto")[
                            htpy.div(".input-group")[
                                htpy.span(".input-group-text")["from"],
                                htpy.input(
                                    ".form-control",
                                    aria_label="Start date",
                                    name="start_date",
                                    type="date",
                                    value=flask.g.start_date.isoformat(),
                                ),
                            ]
                        ],
                        htpy.div(".col-auto")[
                            htpy.div(".input-group")[
                                htpy.span(".input-group-text")["to"],
                                htpy.input(
                                    ".form-control",
                                    aria_label="End date",
                                    name="end_date",
                                    type="date",
                                    value=flask.g.end_date.isoformat(),
                                ),
                            ]
                        ],
                        htpy.div(".col-auto")[
                            htpy.button(".btn.btn-success", type="submit")["Go"]
                        ],
                    ]
                ]
            ]
        ],
        htpy.div(".pt-3.row")[
            htpy.div(".col.col-sm-8.col-md-6.col-lg-5.col-xl-4.col-xxl-3")[
                htpy.table(".table.table-striped")[
                    htpy.tbody[
                        htpy.tr[
                            htpy.td[
                                htpy.div(".g-1.justify-content-between.row")[
                                    htpy.div(".col-auto")[htpy.strong["Total"]],
                                    htpy.div(".col-auto")[
                                        htpy.strong[f"$ {flask.g.total:,.2f}"]
                                    ],
                                ]
                            ]
                        ],
                        expense_rows,
                    ]
                ]
            ]
        ],
    ]
    return signed_in(
        flask.g.email, flask.g.permissions, _back_to_home(), content, "Yavin / Expenses"
    )


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
    return signed_in(email, permissions, _breadcrumb(), content, "Yavin")


def index_signed_out() -> str:
    return str(_base())


def jar() -> str:
    content = [
        _page_title("Jar"),
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.form(action=flask.url_for("jar_add"), method="post")[
                    htpy.div(".g-1.row")[
                        htpy.div(".col-auto")[
                            htpy.input(
                                ".form-control",
                                name="entry_date",
                                title="Entry date",
                                type="date",
                                value=yavin.util.today().isoformat(),
                            )
                        ],
                        htpy.div(".col-auto")[
                            htpy.button(".btn.btn-success", type="submit")["Save"]
                        ],
                    ]
                ]
            ]
        ],
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.h4["Days since last entry: ", flask.g.days_since_last]
            ]
        ],
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.table(".d-block.table")[
                    htpy.thead[htpy.tr[htpy.th["Date"]]],
                    htpy.tbody(hx_post=flask.url_for("jar_rows"), hx_trigger="load")[
                        htpy.tr[
                            htpy.td(".py-3.text-center")[
                                htpy.span(
                                    ".htmx-indicator.spinner-border.spinner-border-sm"
                                )
                            ]
                        ]
                    ],
                ]
            ]
        ],
    ]
    return signed_in(
        flask.g.email, flask.g.permissions, _back_to_home(), content, "Yavin / Jar"
    )


def jar_rows() -> str:
    rows = []
    for i, r in enumerate(flask.g.rows):
        if i < 11:
            rows.append(htpy.tr[htpy.td[r.get("entry_date").isoformat()]])
        else:
            rows.append(
                htpy.tr[
                    htpy.td(
                        ".py-3.text-center",
                        hx_post=flask.url_for("jar_rows", page=flask.g.page + 1),
                        hx_swap="outerHTML",
                        hx_target="closest tr",
                        hx_trigger="revealed",
                    )[htpy.span(".htmx-indicator.spinner-border.spinner-border-sm")]
                ]
            )
    if not rows:
        rows.append(htpy.tr(".text-center")[htpy.td["No entries found."]])
    return str(htpy.fragment[rows])


def library() -> str:
    rows = []
    for b in flask.g.library_books:
        rows.append(
            htpy.tr[
                htpy.td[b.due.isoformat()],
                htpy.td[htpy.span(".badge.bg-dark")[b.medium], " ", b.title],
                htpy.td[b.display_name],
            ]
        )
    content = [
        _page_title("Library"),
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.a(
                    ".btn.btn-primary.mb-2.me-1", href=flask.url_for("library_accounts")
                )[htpy.i(".bi-person-badge"), " Manage accounts"],
                htpy.a(
                    ".btn.btn-primary.mb-2.me-1", href=flask.url_for("library_sync_now")
                )[htpy.i(".bi-arrow-repeat"), " Sync now"],
                htpy.a(
                    ".btn.btn-primary.mb-2.me-1",
                    href=flask.url_for("library_notify_now"),
                )[htpy.i(".bi-bell"), " Notify now"],
            ]
        ],
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.table(".d-block.table")[
                    htpy.thead[
                        htpy.tr[htpy.th["Due"], htpy.th["Title"], htpy.th["Account"]]
                    ],
                    htpy.tbody[rows],
                ]
            ]
        ],
    ]
    return signed_in(
        flask.g.email, flask.g.permissions, _back_to_home(), content, "Yavin / Library"
    )


def library_accounts() -> str:
    rows = []
    for cred in flask.g.library_credentials:
        rows.append(
            htpy.tr[
                htpy.td[cred.get("display_name")],
                htpy.td[cred.get("library")],
                htpy.td[cred.get("library_type")],
                htpy.td[cred.get("username")],
                htpy.td["***"],
                htpy.td[cred.get("balance"), markupsafe.Markup("&cent;")],
                htpy.td[
                    htpy.form(
                        action=flask.url_for("library_accounts_delete"), method="post"
                    )[
                        htpy.input(name="id", type="hidden", value=str(cred.get("id"))),
                        htpy.button(".btn.btn-danger.btn-sm", type="submit")[
                            htpy.i(".bi-trash-fill")
                        ],
                    ]
                ],
            ]
        )
    form_row = htpy.tr[
        htpy.td[
            htpy.form(
                "#form-add-library",
                action=flask.url_for("library_accounts_add"),
                method="post",
            )[
                htpy.input(
                    ".form-control",
                    aria_label="Name",
                    name="display_name",
                    placeholder="Name",
                    required=True,
                    type="text",
                )
            ]
        ],
        htpy.td[
            htpy.input(
                ".form-control",
                aria_label="Library",
                form="form-add-library",
                name="library",
                placeholder="Library",
                required=True,
                type="text",
            )
        ],
        htpy.td[
            htpy.select(
                ".form-select",
                aria_label="Library type",
                form="form-add-library",
                name="library_type",
            )[htpy.option["bibliocommons"], htpy.option(selected=True)["biblionix"]]
        ],
        htpy.td[
            htpy.input(
                ".form-control",
                aria_label="Username",
                form="form-add-library",
                name="username",
                placeholder="Username",
                required=True,
                type="text",
            )
        ],
        htpy.td[
            htpy.input(
                ".form-control",
                aria_label="Password",
                form="form-add-library",
                name="password",
                placeholder="Password",
                required=True,
                type="password",
            )
        ],
        htpy.td,
        htpy.td[
            htpy.button(".btn.btn-success", form="form-add-library", type="submit")[
                htpy.i(".bi-plus-circle")
            ]
        ],
    ]
    content = [
        _page_title("Library accounts"),
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.table(".d-block.table")[
                    htpy.thead[
                        htpy.tr[
                            htpy.th["Name"],
                            htpy.th["Library"],
                            htpy.th["Type"],
                            htpy.th["Username"],
                            htpy.th["Password"],
                            htpy.th["Balance"],
                            htpy.th["Actions"],
                        ]
                    ],
                    htpy.tbody[rows, form_row],
                ]
            ]
        ],
    ]
    return signed_in(
        flask.g.email,
        flask.g.permissions,
        _back_to_library(),
        content,
        "Yavin / Library accounts",
    )


def movie_night(picks: list[dict], people: list[dict]) -> str:
    title = "Movie night"
    content = [
        _page_title(title),
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.button(
                    ".btn.btn-primary.me-1",
                    data_bs_target="#modal-pick",
                    data_bs_toggle="modal",
                    hx_post=flask.url_for("movie_night_modal_pick"),
                    hx_target="#modal-pick-dialog",
                )["Add pick"],
                htpy.a(
                    ".btn.btn-primary",
                    data_bs_toggle="modal",
                    href="#modal-manage-people",
                )["Manage people"],
            ]
        ],
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.table(".d-block.table.table-borderless")[
                    htpy.tbody[
                        (
                            htpy.tr[
                                htpy.td[
                                    pick.get("person"),
                                    " picked ",
                                    htpy.a(
                                        href=pick.get("pick_url"),
                                        rel="noopener",
                                        target="_blank",
                                    )[pick.get("pick_text")]
                                    if pick.get("pick_url")
                                    else pick.get("pick_text"),
                                    " on ",
                                    pick.get("pick_date").strftime("%B "),
                                    pick.get("pick_date").day,
                                    ", ",
                                    pick.get("pick_date").year,
                                    ".",
                                ],
                                htpy.td(".text-end")[
                                    htpy.button(
                                        ".btn.btn-primary.btn-sm",
                                        data_bs_target="#modal-pick",
                                        data_bs_toggle="modal",
                                        hx_post=flask.url_for("movie_night_modal_pick"),
                                        hx_target="#modal-pick-dialog",
                                        name="pick-id",
                                        value=str(pick.get("id")),
                                    )[htpy.i(".bi-pencil-fill")]
                                ],
                            ]
                            for pick in picks
                        )
                    ]
                ]
            ]
        ],
        htpy.div("#modal-pick.modal")[htpy.div("#modal-pick-dialog.modal-dialog")],
        htpy.div("#modal-manage-people.modal")[
            htpy.div(".modal-dialog")[
                htpy.div(".modal-content")[
                    htpy.div(".modal-header")[htpy.h5(".modal-title")["People"]],
                    htpy.div(".modal-body")[
                        htpy.table(".table")[
                            htpy.thead[htpy.tr[htpy.th["Name"], htpy.th]],
                            htpy.tbody[
                                (
                                    htpy.tr[htpy.td[p.get("person")], htpy.td]
                                    for p in people
                                ),
                                htpy.tr[
                                    htpy.td[
                                        htpy.form(
                                            "#form-add-person",
                                            action=flask.url_for(
                                                "movie_night_add_person"
                                            ),
                                            method="post",
                                        )[
                                            htpy.input(
                                                ".form-control",
                                                aria_label="Name",
                                                name="person",
                                                placeholder="Name",
                                                required=True,
                                                type="text",
                                            )
                                        ]
                                    ],
                                    htpy.td(".text-end")[
                                        htpy.button(
                                            ".btn.btn-success",
                                            form="form-add-person",
                                            type="submit",
                                        )["Add"]
                                    ],
                                ],
                            ],
                        ]
                    ],
                    htpy.div(".modal-footer")[
                        htpy.button(
                            ".btn.btn-secondary", data_bs_dismiss="modal", type="button"
                        )["Cancel"]
                    ],
                ]
            ]
        ],
    ]
    return signed_in(
        flask.g.email, flask.g.permissions, _back_to_home(), content, f"Yavin / {title}"
    )


def movie_night_modal_pick(people: list[dict], pick: dict = None) -> str:
    content = htpy.div(".modal-content")[
        htpy.div(".modal-header")[
            htpy.h5(".modal-title")[
                "Edit this movie pick" if pick else "Add a movie pick"
            ]
        ],
        htpy.div(".modal-body")[
            htpy.form(
                "#form-pick",
                action=flask.url_for(
                    "movie_night_edit_pick" if pick else "movie_night_add_pick"
                ),
                method="post",
            )[
                pick
                and htpy.input(name="id", type="hidden", value=str(pick.get("id"))),
                htpy.div(".mb-3")[
                    htpy.label(".form-label", for_="pick-date")["When"],
                    htpy.input(
                        "#pick-date.form-control",
                        name="pick_date",
                        required=True,
                        type="date",
                        value=pick.get("pick_date").isoformat()
                        if pick
                        else yavin.util.today().isoformat(),
                    ),
                ],
                htpy.div(".mb-3")[
                    htpy.label(".form-label", for_="person-id")["Who"],
                    htpy.select(
                        "#person-id.form-select", name="person_id", required=True
                    )[
                        (
                            htpy.option(
                                selected=pick.get("person_id") == p.get("id")
                                if pick
                                else p.get("pick_order") == 1,
                                value=str(p.get("id")),
                            )[p.get("person")]
                            for p in people
                        )
                    ],
                ],
                htpy.div(".mb-3")[
                    htpy.label(".form-label", for_="pick-text")["What"],
                    htpy.input(
                        "#pick-text.form-control",
                        name="pick_text",
                        required=True,
                        type="text",
                        value=pick and pick.get("pick_text"),
                    ),
                ],
                htpy.div(".mb-3")[
                    htpy.label(".form-label", for_="pick-url")["URL"],
                    htpy.input(
                        "#pick-url.form-control",
                        name="pick_url",
                        type="text",
                        value=pick and pick.get("pick_url"),
                    ),
                ],
            ]
        ],
        htpy.div(".justify-content-between.modal-footer")[
            htpy.button(".btn.btn-secondary", data_bs_dismiss="modal")["Cancel"],
            pick
            and htpy.button(
                ".btn.btn-danger",
                form="form-pick",
                formaction=flask.url_for("movie_night_delete_pick"),
            )["Delete"],
            htpy.button(".btn.btn-success", form="form-pick")["Save"],
        ],
    ]
    return str(content)


def not_authorized(email: str, permissions: list[str]) -> str:
    content = htpy.div(".row")[
        htpy.div(".col")[
            htpy.h1["Not authorized"],
            htpy.p(".lead")["You are not authorized to view this page."],
        ]
    ]
    return signed_in(email, permissions, _back_to_home(), content)


def phone() -> str:
    rows = (
        htpy.tr[
            htpy.td[record.get("start_date").isoformat()],
            htpy.td[record.get("end_date").isoformat()],
            htpy.td(".text-end")[record.get("minutes")],
            htpy.td(".text-end")[record.get("messages")],
            htpy.td(".text-end")[record.get("megabytes")],
        ]
        for record in flask.g.records
    )
    form = htpy.form(
        "#form-add-phone-usage", action=flask.url_for("phone_add"), method="post"
    )[
        htpy.div(".mb-3")[
            htpy.label(".form-label", for_="start-date")["Start date"],
            htpy.input(
                "#start-date.form-control",
                name="start-date",
                required=True,
                type="date",
            ),
        ],
        htpy.div(".mb-3")[
            htpy.label(".form-label", for_="end-date")["End date"],
            htpy.input(
                "#end-date.form-control",
                name="end-date",
                required=True,
                type="date",
            ),
        ],
        htpy.div(".mb-3")[
            htpy.label(".form-label", for_="minutes")["Minutes"],
            htpy.input(
                "#minutes.form-control",
                min=0,
                name="minutes",
                required=True,
                step=1,
                type="number",
            ),
        ],
        htpy.div(".mb-3")[
            htpy.label(".form-label", for_="messages")["Messages"],
            htpy.input(
                "#messages.form-control",
                min=0,
                name="messages",
                required=True,
                step=1,
                type="number",
            ),
        ],
        htpy.div(".mb-3")[
            htpy.label(".form-label", for_="megabytes")["Megabytes"],
            htpy.input(
                "#megabytes.form-control",
                min=0,
                name="megabytes",
                required=True,
                step=1,
                type="number",
            ),
        ],
    ]
    content = [
        _page_title("Phone usage"),
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.a(
                    ".btn.btn-primary",
                    data_bs_toggle="modal",
                    href="#modal-add-phone-usage",
                )["Add usage"]
            ]
        ],
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.table(".d-block.table")[
                    htpy.thead[
                        htpy.tr[
                            htpy.th["Start date"],
                            htpy.th["End date"],
                            htpy.th(".text-end")["Minutes"],
                            htpy.th(".text-end")["Messages"],
                            htpy.th(".text-end")["Megabytes"],
                        ]
                    ],
                    htpy.tbody[rows],
                ]
            ]
        ],
        htpy.div("#modal-add-phone-usage.modal")[
            htpy.div(".modal-dialog")[
                htpy.div(".modal-content")[
                    htpy.div(".modal-header")[
                        htpy.h5(".modal-title")["Add phone usage"]
                    ],
                    htpy.div(".modal-body")[form],
                    htpy.div(".justify-content-between.modal-footer")[
                        htpy.button(
                            ".btn.btn-secondary", data_bs_dismiss="modal", type="button"
                        )["Cancel"],
                        htpy.button(
                            ".btn.btn-success",
                            form="form-add-phone-usage",
                            type="submit",
                        )["Add usage"],
                    ],
                ]
            ]
        ],
    ]
    return signed_in(
        flask.g.email,
        flask.g.permissions,
        _back_to_home(),
        content,
        "Yavin / Phone usage",
    )


def signed_in(
    email: str, permissions: list[str], breadcrumb=None, content=None, title=None
) -> str:
    is_admin = "admin" in permissions
    content = _base(
        title,
        sign_in_block=_user_menu(email, is_admin),
        breadcrumb=breadcrumb,
        content=content,
    )
    return str(content)


def tithing() -> str:
    content = [
        _page_title("Tithing"),
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.p[
                    "Current tithing owed: ",
                    htpy.strong[f"$ {flask.g.tithing_owed:,.2f}"],
                ]
            ]
        ],
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.a(
                    ".btn.btn-success.mb-1.me-1",
                    data_bs_toggle="modal",
                    href="#modal-add-tx",
                )[htpy.i(".bi-piggy-bank"), " Add income transaction"],
                htpy.a(
                    ".btn.btn-primary.mb-1.me-1",
                    data_bs_toggle="modal",
                    href="#modal-mark-paid",
                )[htpy.i(".bi-cash-coin"), " Mark tithing paid"],
            ]
        ],
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.table(".d-block.table.table-striped")[
                    htpy.thead[
                        htpy.tr[
                            htpy.th["Date"],
                            htpy.th["Description"],
                            htpy.th(".text-end")["Amount"],
                        ]
                    ],
                    htpy.tbody[
                        (
                            htpy.tr[
                                htpy.td[t.get("date").isoformat()],
                                htpy.td[t.get("description")],
                                htpy.td(".text-end")[f"$ {t.get('amount'):,.2f}"],
                            ]
                            for t in flask.g.transactions
                        )
                    ],
                ]
            ]
        ],
        htpy.div("#modal-add-tx.modal")[
            htpy.div(".modal-dialog")[
                htpy.div(".modal-content")[
                    htpy.div(".modal-header")[
                        htpy.h5(".modal-title")["Add a transaction"]
                    ],
                    htpy.div(".modal-body")[
                        htpy.form(
                            "#form-add-tx",
                            action=flask.url_for("tithing_income_add"),
                            method="post",
                        )[
                            htpy.div(".mb-3")[
                                htpy.label(".form-label", for_="tx-date")["Date"],
                                htpy.input(
                                    "#tx-date.form-control",
                                    name="tx-date",
                                    required=True,
                                    type="date",
                                    value=yavin.util.today().isoformat(),
                                ),
                            ],
                            htpy.div(".mb-3")[
                                htpy.label(".form-label", for_="tx-description")[
                                    "Description"
                                ],
                                htpy.input(
                                    "#tx-description.form-control",
                                    name="tx-description",
                                    required=True,
                                    type="text",
                                ),
                            ],
                            htpy.div(".mb-3")[
                                htpy.label(".form-label", for_="tx-value")["Amount"],
                                htpy.input(
                                    "#tx-value.form-control",
                                    name="tx-value",
                                    required=True,
                                    step="0.01",
                                    type="number",
                                ),
                            ],
                        ]
                    ],
                    htpy.div(".justify-content-between.modal-footer")[
                        htpy.button(".btn.btn-secondary", data_bs_dismiss="modal")[
                            "Cancel"
                        ],
                        htpy.button(
                            ".btn.btn-success", form="form-add-tx", type="submit"
                        )["Add transaction"],
                    ],
                ]
            ]
        ],
        htpy.div("#modal-mark-paid.modal")[
            htpy.div(".modal-dialog")[
                htpy.div(".modal-content")[
                    htpy.div(".modal-header")[
                        htpy.h5(".modal-title")["Mark all tithing paid"]
                    ],
                    htpy.div(".justify-content-between.modal-footer")[
                        htpy.button(".btn.btn-secondary", data_bs_dismiss="modal")[
                            "Cancel"
                        ],
                        htpy.form(
                            action=flask.url_for("tithing_income_paid"), method="post"
                        )[htpy.button(".btn.btn-success", type="submit")["Apply"]],
                    ],
                ]
            ]
        ],
    ]
    return signed_in(
        flask.g.email, flask.g.permissions, _back_to_home(), content, "Yavin / Tithing"
    )


def user_permissions() -> str:
    content = [
        _page_title("User permissions"),
        htpy.div(".pt-3.row")[
            htpy.div(".col-12.col-sm-10.col-md-8.col-lg-7.col-xl-4")[
                htpy.table(".table")[
                    htpy.thead[htpy.tr[htpy.th["Email"], htpy.th["Permissions"]]],
                    htpy.tbody[
                        (
                            htpy.tr[
                                htpy.td[u.get("email")],
                                htpy.td[
                                    (htpy.code[p, " "] for p in u.get("permissions"))
                                ],
                            ]
                            for u in flask.g.users
                        )
                    ],
                ]
            ]
        ],
    ]
    return signed_in(
        flask.g.email,
        flask.g.permissions,
        _back_to_home(),
        content,
        "Yavin / User permissions",
    )


def weight(weight_entries: list[dict], default_weight: decimal.Decimal) -> str:
    messages = flask.get_flashed_messages(with_categories=True)
    log.debug(messages)
    content = [
        _page_title("Weight"),
        messages
        and htpy.div(".pt-3.row")[
            htpy.div(".col")[
                (
                    htpy.div(f".alert.alert-dismissible.{category}")[
                        htpy.button(
                            ".btn-close", data_bs_dismiss="alert", type="button"
                        ),
                        message,
                    ]
                    for category, message in messages
                )
            ]
        ],
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.form(action=flask.url_for("weight_add"), method="post")[
                    htpy.div(".g-1.row")[
                        htpy.div(".col-auto")[
                            htpy.input(
                                ".form-control",
                                name="entry_date",
                                required=True,
                                title="Entry date",
                                type="date",
                                value=yavin.util.today().isoformat(),
                            )
                        ],
                        htpy.div(".col-auto")[
                            htpy.div(".input-group")[
                                htpy.input(
                                    ".form-control",
                                    min=1,
                                    name="weight",
                                    required=True,
                                    step="any",
                                    title="Weight",
                                    type="number",
                                    value=str(default_weight),
                                ),
                                htpy.span(".input-group-text")["lbs"],
                            ]
                        ],
                        htpy.div(".col-auto")[
                            htpy.button(".btn.btn-success", type="submit")["Save"]
                        ],
                    ]
                ]
            ]
        ],
        htpy.div(".pt-3.row")[
            htpy.div(".col")[
                htpy.table(".d-block.table")[
                    htpy.thead[htpy.tr[htpy.th["Date"], htpy.th["Weight"]]],
                    htpy.tbody[
                        (
                            htpy.tr[
                                htpy.td[entry.get("entry_date").isoformat()],
                                htpy.td[str(entry.get("weight"))],
                            ]
                            for entry in weight_entries
                        )
                    ],
                ]
            ]
        ],
    ]
    return signed_in(
        flask.g.email, flask.g.permissions, _back_to_home(), content, "Yavin / Weight"
    )
