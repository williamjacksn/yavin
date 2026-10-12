"""Disney Dreamlight Valley character roster and editable lookup lists."""

import uuid
from collections import Counter

import flask
import htpy as h
import psycopg2
from werkzeug import Response

from yavin import components

KINDS = {"area": "Areas", "universe": "Universes", "skill": "Skills"}
FILTERS = ("name", "area", "universe", "skill")


def filters() -> dict[str, str]:
    return {key: flask.request.args.get(key, "") for key in FILTERS}


def action_url(endpoint: str, **values: str) -> str:
    # These dictionaries contain route variables and filters, not Flask options.
    return flask.url_for(endpoint, **values, **filters())  # ty:ignore[invalid-argument-type]


def selected_id(value: str, entries: list[dict], label: str) -> uuid.UUID:
    try:
        entry_id = uuid.UUID(value)
    except ValueError:
        raise ValueError(f"Choose a valid {label}.") from None
    if not any(entry["id"] == entry_id for entry in entries):
        raise ValueError(f"Choose a valid {label}.")
    return entry_id


def valid_name(
    value: str, entries: list[dict], entry_id: uuid.UUID | None = None
) -> str:
    name = value.strip()
    if not name:
        raise ValueError("Name is required.")
    if any(
        entry["name"].casefold() == name.casefold() and entry["id"] != entry_id
        for entry in entries
    ):
        raise ValueError("That name already exists.")
    return name


def mutation_error(error: Exception) -> tuple[str, int]:
    message = (
        "The list changed or this name is already used. Review the current lists "
        "and try again. Referenced Areas and Universes cannot be changed; "
        "assigned Skills cannot be deleted."
        if isinstance(error, psycopg2.IntegrityError)
        else str(error)
    )
    return page(message), 400


def character_add() -> str | tuple[str, int] | Response:
    db = flask.g.db
    values = flask.request.form
    try:
        name = valid_name(values.get("name", ""), db.dreamlight_characters_list())
        area_id = selected_id(
            values.get("area_id", ""), db.dreamlight_lookup_list("area"), "Area"
        )
        universe_id = selected_id(
            values.get("universe_id", ""),
            db.dreamlight_lookup_list("universe"),
            "Universe",
        )
        db.dreamlight_character_add(name, area_id, universe_id)
    except (ValueError, psycopg2.IntegrityError) as error:
        return mutation_error(error)
    return flask.redirect(action_url("dreamlight"))


def character_update(
    character_id: uuid.UUID, action: str
) -> str | tuple[str, int] | Response:
    if action not in ("skill", "delete"):
        flask.abort(404)
    db = flask.g.db
    if not any(c["id"] == character_id for c in db.dreamlight_characters_list()):
        flask.abort(404)
    try:
        if action == "delete":
            db.dreamlight_character_delete(character_id)
        else:
            value = flask.request.form.get("skill_id", "")
            skill_id = (
                selected_id(value, db.dreamlight_lookup_list("skill"), "Skill")
                if value
                else None
            )
            db.dreamlight_character_skill(character_id, skill_id)
    except (ValueError, psycopg2.IntegrityError) as error:
        return mutation_error(error)
    return flask.redirect(action_url("dreamlight"))


def lookup_update(kind: str, action: str) -> str | tuple[str, int] | Response:
    if kind not in KINDS or action not in ("add", "rename", "delete"):
        flask.abort(404)
    db = flask.g.db
    entries = db.dreamlight_lookup_list(kind)
    try:
        entry_id = None
        if action != "add":
            entry_id = selected_id(flask.request.form.get("id", ""), entries, kind)
            used = any(
                c[f"{kind}_id"] == entry_id for c in db.dreamlight_characters_list()
            )
            if used and (action == "delete" or kind != "skill"):
                raise ValueError(
                    "This entry is used by a character. Clear Skill assignments "
                    "before deleting a Skill. Areas and Universes stay fixed "
                    "while characters reference them."
                )
        if action == "delete":
            db.dreamlight_lookup_delete(kind, entry_id)
        else:
            name = valid_name(flask.request.form.get("name", ""), entries, entry_id)
            db.dreamlight_lookup_save(kind, name, entry_id)
    except (ValueError, psycopg2.IntegrityError) as error:
        return mutation_error(error)
    return flask.redirect(action_url("dreamlight") + "#lists")


def select(
    name: str,
    label: str,
    entries: list[dict],
    value: str = "",
    blank: str = "Choose…",
    required: bool = False,
    control_id: str | None = None,
) -> h.Element:
    control_id = control_id or name
    return h.div[
        h.label(".form-label", for_=control_id)[label],
        h.select(".form-select", id=control_id, name=name, required=required)[
            h.option(value="", selected=value == "")[blank],
            h.option(value="unassigned", selected=value == "unassigned")["Unassigned"]
            if name == "skill"
            else None,
            [
                h.option(value=str(e["id"]), selected=value == str(e["id"]))[e["name"]]
                for e in entries
            ],
        ],
    ]


def lookup_panel(kind: str, entries: list[dict], characters: list[dict]) -> h.Element:
    used = {c[f"{kind}_id"] for c in characters}
    values = (
        flask.request.form
        if flask.request.view_args == {"kind": kind, "action": "add"}
        else {}
    )
    return h.section(".col-12.col-lg-4")[
        h.h3(".h5")[KINDS[kind]],
        h.form(
            ".d-flex.gap-2.mb-3",
            action=action_url("dreamlight_lookup_update", kind=kind, action="add"),
            method="post",
        )[
            h.input(
                ".form-control",
                name="name",
                required=True,
                aria_label=f"New {kind} name",
                placeholder=f"New {kind} name",
                value=values.get("name", ""),
            ),
            h.button(".btn.btn-success", type="submit")["Add"],
        ],
        h.ul(".list-group")[
            [
                h.li(".list-group-item")[
                    h.form(
                        ".d-flex.gap-2.align-items-center",
                        action=action_url(
                            "dreamlight_lookup_update", kind=kind, action="rename"
                        ),
                        method="post",
                    )[
                        h.input(type="hidden", name="id", value=str(e["id"])),
                        h.input(
                            ".form-control",
                            name="name",
                            value=e["name"],
                            required=True,
                            aria_label=f"{kind.title()} name",
                            readonly=kind != "skill" and e["id"] in used,
                        ),
                        h.button(
                            ".btn.btn-sm.btn-outline-primary",
                            type="submit",
                            disabled=kind != "skill" and e["id"] in used,
                        )["Rename"],
                        h.button(
                            ".btn.btn-sm.btn-outline-danger",
                            type="submit",
                            formaction=action_url(
                                "dreamlight_lookup_update", kind=kind, action="delete"
                            ),
                            disabled=e["id"] in used,
                            onclick="return confirm('Delete this list entry?')",
                        )["Delete"],
                    ],
                    h.small(".text-body-secondary")["In use by a character"]
                    if e["id"] in used
                    else None,
                ]
                for e in entries
            ]
            or h.li(".list-group-item.text-body-secondary")["No entries yet."],
        ],
    ]


def page(error: str = "") -> str:
    db = flask.g.db
    lists = {kind: db.dreamlight_lookup_list(kind) for kind in KINDS}
    characters = db.dreamlight_characters_list()
    query = filters()
    filtered = [
        c
        for c in characters
        if query["name"].strip().casefold() in c["name"].casefold()
        and all(
            not query[kind]
            or (
                kind == "skill"
                and query[kind] == "unassigned"
                and c["skill_id"] is None
            )
            or query[kind] == str(c[f"{kind}_id"])
            for kind in KINDS
        )
    ]
    counts = Counter(c["skill_id"] for c in characters)
    values = (
        flask.request.form
        if flask.request.endpoint == "dreamlight_character_add"
        else {}
    )
    content = h.main[
        h.h1(".mt-3")["Disney Dreamlight Valley"],
        h.p(".text-body-secondary")[
            "Track characters and assign their companion Skills."
        ],
        h.div(".alert.alert-danger", role="alert")[error] if error else None,
        h.h2(".h4")["Skill assignments"],
        h.p(".text-body-secondary")[
            "Totals for all characters, regardless of filters."
        ],
        h.div(".d-flex.flex-wrap.gap-2.mb-4")[
            h.a(
                ".btn.btn-outline-secondary",
                href=flask.url_for("dreamlight", skill="unassigned"),
            )[f"Unassigned: {counts[None]}"],
            [
                h.a(
                    ".btn.btn-outline-primary",
                    href=flask.url_for("dreamlight", skill=str(s["id"])),
                )[f"{s['name']}: {counts[s['id']]}"]
                for s in lists["skill"]
            ],
        ],
        h.h2(".h4")["Characters"],
        h.form(".row.g-3.mb-3", method="get", action=flask.url_for("dreamlight"))[
            h.div(".col-12.col-md-3")[
                h.label(".form-label", for_="filter-name")["Search name"],
                h.input(
                    "#filter-name.form-control",
                    name="name",
                    value=query["name"],
                    type="search",
                ),
            ],
            [
                h.div(".col-12.col-md-3")[
                    select(
                        kind,
                        kind.title(),
                        lists[kind],
                        query[kind],
                        "All",
                        control_id=f"filter-{kind}",
                    )
                ]
                for kind in KINDS
            ],
            h.div(".col-12.d-flex.gap-2")[
                h.button(".btn.btn-primary", type="submit")["Filter"],
                h.a(".btn.btn-outline-secondary", href=flask.url_for("dreamlight"))[
                    "Clear filters"
                ],
            ],
        ],
        h.p[f"Showing {len(filtered)} of {len(characters)} characters"],
        h.div(".table-responsive")[
            h.table(".table.table-striped.align-middle")[
                h.thead[
                    h.tr[
                        [
                            h.th(scope="col")[label]
                            for label in (
                                "Name",
                                "Universe",
                                "Area",
                                "Skill",
                                "Actions",
                            )
                        ]
                    ]
                ],
                h.tbody[
                    [
                        h.tr[
                            h.th(scope="row")[c["name"]],
                            h.td[c["universe"]],
                            h.td[c["area"]],
                            h.td[
                                h.form(
                                    ".d-flex.gap-2.align-items-end",
                                    action=action_url(
                                        "dreamlight_character_update",
                                        character_id=str(c["id"]),
                                        action="skill",
                                    ),
                                    method="post",
                                )[
                                    select(
                                        "skill_id",
                                        f"Skill for {c['name']}",
                                        lists["skill"],
                                        str(c["skill_id"]) if c["skill_id"] else "",
                                        "Unassigned",
                                        control_id=f"skill-{c['id']}",
                                    ),
                                    h.button(".btn.btn-outline-primary", type="submit")[
                                        "Save"
                                    ],
                                ],
                            ],
                            h.td[
                                h.form(
                                    action=action_url(
                                        "dreamlight_character_update",
                                        character_id=str(c["id"]),
                                        action="delete",
                                    ),
                                    method="post",
                                    onsubmit="return confirm('Delete this character?')",
                                )[
                                    h.button(
                                        ".btn.btn-sm.btn-outline-danger", type="submit"
                                    )["Delete"]
                                ],
                            ],
                        ]
                        for c in filtered
                    ]
                    or h.tr[
                        h.td(colspan=5)[
                            "No characters match these filters."
                            if characters
                            else "Add Areas and Universes below, "
                            "then add your first character."
                        ]
                    ],
                ],
            ],
        ],
        h.h2(".h4.mt-4")["Add character"],
        h.p[
            "Name, Universe, and Area are fixed after creation. "
            "New characters have no Skill."
        ],
        h.form(
            ".row.g-3.mb-4",
            action=action_url("dreamlight_character_add"),
            method="post",
        )[
            h.div(".col-12.col-md-4")[
                h.label(".form-label", for_="character-name")["Name"],
                h.input(
                    "#character-name.form-control",
                    name="name",
                    required=True,
                    value=values.get("name", ""),
                ),
            ],
            [
                h.div(".col-12.col-md-4")[
                    select(
                        f"{kind}_id",
                        kind.title(),
                        lists[kind],
                        values.get(f"{kind}_id", ""),
                        required=True,
                    )
                ]
                for kind in ("universe", "area")
            ],
            h.div(".col-12")[
                h.button(
                    ".btn.btn-success",
                    type="submit",
                    disabled=not lists["area"] or not lists["universe"],
                )["Add character"]
            ],
        ],
        h.h2("#lists.h4.mt-4")["Manage lists"],
        h.p[
            "Areas and Universes in use cannot be renamed or deleted. "
            "Clear assignments before deleting a Skill."
        ],
        h.div(".row.g-4.mb-4")[
            [lookup_panel(kind, lists[kind], characters) for kind in KINDS]
        ],
    ]
    return components.signed_in(
        flask.g.email,
        flask.g.permissions,
        components._back_to_home(),
        content,
        "Yavin / Disney Dreamlight Valley",
    )
