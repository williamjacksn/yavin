"""Musical theatre log: one entry per performer and production."""

import csv
import datetime
import io
import json
import uuid
from collections.abc import Mapping

import flask
import htpy as h
from werkzeug import Response

from yavin import components

FIELDS = {
    "performer": "Performer",
    "show": "Show",
    "first_show": "First show",
    "last_show": "Last show",
    "performances": "Performances",
    "role": "Role",
    "company": "Company",
    "director": "Director",
}


def validate(values: Mapping[str, str]) -> dict:
    entry = {key: values.get(key, "").strip() for key in FIELDS}
    for key in ("performer", "show"):
        if not entry[key]:
            raise ValueError(f"{FIELDS[key]} is required.")
    result: dict = dict(entry)
    for key in ("first_show", "last_show"):
        try:
            result[key] = (
                datetime.date.fromisoformat(entry[key]) if entry[key] else None
            )
        except ValueError:
            raise ValueError(f"{FIELDS[key]} must be a valid date.") from None
    if (
        result["first_show"]
        and result["last_show"]
        and result["last_show"] < result["first_show"]
    ):
        raise ValueError("Last show must be on or after first show.")
    try:
        count = int(entry["performances"]) if entry["performances"] else None
        if count is not None and not 0 <= count <= 2147483647:
            raise ValueError
    except ValueError:
        raise ValueError("Performances must be a nonnegative whole number.") from None
    result["performances"] = count
    return result


def parse_csv(text: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
    if reader.fieldnames != list(FIELDS.values()):
        raise ValueError("CSV columns must match the exported template.")
    entries = []
    for row in reader:
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f"CSV row {reader.line_num} has the wrong column count.")
        try:
            entries.append(validate({key: row[label] for key, label in FIELDS.items()}))
        except ValueError as error:
            raise ValueError(f"CSV row {reader.line_num}: {error}") from error
    return entries


def entry_form(
    values: Mapping | None = None, error: str = "", entry_id: uuid.UUID | None = None
) -> str:
    entries = flask.g.db.theatre_list()
    values = values or {}
    controls = []
    for key, label in FIELDS.items():
        kind = "date" if key in ("first_show", "last_show") else "text"
        if key == "performances":
            kind = "number"
        attributes = (
            {"min": 0, "max": 2147483647, "step": 1} if kind == "number" else {}
        )
        if kind == "text":
            attributes["list"] = f"{key}-suggestions"
        controls.append(
            h.div(".col-12.col-md-6")[
                h.label(".form-label", for_=key)[label],
                h.input(
                    f"#{key}.form-control",
                    name=key,
                    type=kind,
                    required=key in ("performer", "show"),
                    value=str(values.get(key) if values.get(key) is not None else ""),
                    **attributes,
                ),
                h.datalist(id=f"{key}-suggestions")[
                    [
                        h.option(value=value)
                        for value in sorted(
                            {
                                str(e[key])
                                for e in entries
                                if e[key] is not None and e[key] != ""
                            }
                        )
                    ]
                ],
            ]
        )
    save_url = (
        flask.url_for("theatre_edit", entry_id=entry_id)
        if entry_id
        else flask.url_for("theatre_add")
    )
    title = "Edit entry" if entry_id else "Add entry"
    content = h.div[
        h.h1(".mt-3")[title],
        h.p["Leave unknown dates and counts blank."],
        h.div(".alert.alert-danger", role="alert")[error] if error else None,
        h.form(".row.g-3.mb-4", action=save_url, method="post")[
            controls,
            h.div(".col-12")[
                h.button(".btn.btn-success", type="submit")["Save entry"],
                " ",
                h.a(
                    ".btn.btn-outline-secondary",
                    href=flask.url_for("theatre"),
                )["Cancel"],
            ],
        ],
    ]

    return components.signed_in(
        flask.g.email,
        flask.g.permissions,
        h.a(".btn.btn-outline-dark", href=flask.url_for("theatre"))["Musical theatre"],
        content,
        f"Yavin / Musical theatre / {title}",
    )


def page(error: str = "") -> str:
    entries = flask.g.db.theatre_list()
    selected = flask.request.args.get("performer", "")
    shown = [e for e in entries if not selected or e["performer"] == selected]
    content = h.div[
        h.h1(".mt-3")["Musical theatre"],
        h.p[
            "Record one performer's role in a production. "
            "Leave unknown dates and counts blank."
        ],
        [
            h.div(".alert.alert-success")[message]
            for message in flask.get_flashed_messages()
        ],
        h.div(".alert.alert-danger", role="alert")[error] if error else None,
        h.a(
            ".btn.btn-success.mb-3",
            href=flask.url_for("theatre_add"),
        )["Add entry"],
        h.h2["Performance log"],
        h.div(".input-group.mb-3.w-auto")[
            h.label(".input-group-text", for_="filter-performer")["Performer"],
            h.select(
                "#filter-performer.form-select",
                name="performer",
                hx_get=flask.url_for("theatre"),
                hx_trigger="change",
                hx_target="#theatre-results",
                hx_select="#theatre-results",
                hx_swap="outerHTML",
                hx_push_url="true",
                hx_sync="this:replace",
            )[
                [
                    h.option(value="")["All performers"],
                    [
                        h.option(value=p, selected=p == selected)[p]
                        for p in sorted({e["performer"] for e in entries})
                    ],
                ]
            ],
        ],
        h.div("#theatre-results", aria_live="polite")[
            h.p[
                f"{len(shown)} entries · "
                f"{sum(e['performances'] or 0 for e in shown)} "
                "recorded performer appearances · "
                f"{sum(e['performances'] is None for e in shown)} unknown counts"
            ],
            h.div(".table-responsive")[
                h.table(".table.table-striped")[
                    h.thead[
                        h.tr[
                            [h.th[label] for label in FIELDS.values()], h.th["Actions"]
                        ]
                    ],
                    h.tbody[
                        [
                            h.tr[
                                [
                                    h.td[
                                        str(e[key])
                                        if e[key] is not None and e[key] != ""
                                        else "—"
                                    ]
                                    for key in FIELDS
                                ],
                                h.td[
                                    h.a(
                                        href=flask.url_for(
                                            "theatre_edit", entry_id=e["id"]
                                        ),
                                    )["Edit"]
                                ],
                            ]
                            for e in shown
                        ]
                    ],
                ]
            ]
            if shown
            else h.p["No entries yet for this selection."],
        ],
        h.h2["CSV import and export"],
        h.p[
            "Import the original spreadsheet or an exported file. "
            "Exact matching entries are skipped. Export includes all performers."
        ],
        h.a(".btn.btn-outline-primary.mb-3", href=flask.url_for("theatre_export"))[
            "Export CSV / blank template"
        ],
        h.form(
            method="post",
            action=flask.url_for("theatre_import"),
            enctype="multipart/form-data",
        )[
            h.label(".form-label", for_="csv-file")["CSV file"],
            h.input(
                "#csv-file.form-control.mb-2",
                type="file",
                name="file",
                accept=".csv,text/csv",
                required=True,
            ),
            h.button(".btn.btn-primary", type="submit")["Import CSV"],
        ],
    ]
    return components.signed_in(
        flask.g.email,
        flask.g.permissions,
        h.a(".btn.btn-outline-dark", href=flask.url_for("index"))["Home"],
        content,
        "Yavin / Musical theatre",
    )


def export_csv() -> flask.Response:
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(FIELDS.values())
    for entry in flask.g.db.theatre_list():
        writer.writerow([entry[key] for key in FIELDS])
    return flask.Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=theatre-performances.csv"
        },
    )


def import_csv() -> tuple[str, int] | Response:
    upload = flask.request.files.get("file")
    try:
        if not upload:
            raise ValueError("Choose a CSV file.")
        data = upload.stream.read(2_000_001)
        if len(data) > 2_000_000:
            raise ValueError("CSV must be smaller than 2 MB.")
        entries = parse_csv(data.decode("utf-8-sig"))
    except (UnicodeError, ValueError, csv.Error) as error:
        return page(error=str(error)), 400
    flask.g.db.theatre_import(json.dumps(entries, default=str))
    flask.flash("Import complete. Exact matching entries were skipped.")
    return flask.redirect(flask.url_for("theatre"))
