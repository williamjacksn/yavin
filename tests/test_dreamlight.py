import os
import tempfile
import unittest
import uuid
from unittest.mock import MagicMock, patch

import lxml.html
import psycopg2

with (
    tempfile.TemporaryDirectory() as directory,
    patch.dict(os.environ, {"DATABASE": os.path.join(directory, "test.db")}),
):
    from yavin.app import app

from yavin.db.app import YavinDatabase


class DreamlightTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = MagicMock()
        self.db.settings_list.return_value = {}
        self.db.user_permissions_get.return_value = ["dreamlight"]
        self.lists: dict[str, list[dict]] = {
            "area": [{"id": uuid.uuid4(), "name": "Plaza"}],
            "universe": [{"id": uuid.uuid4(), "name": "Mickey & Friends"}],
            "skill": [
                {"id": uuid.uuid4(), "name": "Mining"},
                {"id": uuid.uuid4(), "name": "Fishing"},
            ],
        }
        self.db.dreamlight_lookup_list.side_effect = self.lists.__getitem__
        self.character = {
            "id": uuid.uuid4(),
            "name": "Mickey Mouse",
            "area_id": self.lists["area"][0]["id"],
            "area": "Plaza",
            "universe_id": self.lists["universe"][0]["id"],
            "universe": "Mickey & Friends",
            "skill_id": None,
            "skill": None,
        }
        self.db.dreamlight_characters_list.return_value = [self.character]
        patcher = patch("yavin.db.YavinDatabase", return_value=self.db)
        patcher.start()
        self.addCleanup(patcher.stop)
        app.config.update(TESTING=True, SECRET_KEY=uuid.uuid4().hex)
        self.client = app.test_client()

    def character_path(self, action: str) -> str:
        return f"/dreamlight/characters/{self.character['id']}/{action}"

    def test_create_always_starts_unassigned_and_trims_name(self) -> None:
        response = self.client.post(
            "/dreamlight/characters/add",
            data={
                "name": "  Minnie Mouse  ",
                "area_id": str(self.character["area_id"]),
                "universe_id": str(self.character["universe_id"]),
                "skill_id": str(self.lists["skill"][0]["id"]),
            },
        )
        self.assertEqual(response.status_code, 302)
        self.db.dreamlight_character_add.assert_called_once_with(
            "Minnie Mouse", self.character["area_id"], self.character["universe_id"]
        )

    def test_rejects_invalid_names_and_references_preserving_input(self) -> None:
        valid = {
            "name": "Minnie",
            "area_id": str(self.character["area_id"]),
            "universe_id": str(self.character["universe_id"]),
        }
        for changes in (
            {"name": " "},
            {"name": " mICKEY mOUSE "},
            {"area_id": "invalid"},
            {"universe_id": str(uuid.uuid4())},
        ):
            with self.subTest(changes=changes):
                response = self.client.post(
                    "/dreamlight/characters/add", data=valid | changes
                )
                self.assertEqual(response.status_code, 400)
                document = lxml.html.fromstring(response.data)
                self.assertEqual(
                    document.get_element_by_id("character-name").get("value"),
                    (valid | changes)["name"],
                )
        self.db.dreamlight_character_add.assert_not_called()

    def test_skill_assign_change_clear_and_identity_is_ignored(self) -> None:
        for skill in self.lists["skill"]:
            response = self.client.post(
                self.character_path("skill"),
                data={
                    "skill_id": str(skill["id"]),
                    "name": "Changed",
                    "area_id": str(uuid.uuid4()),
                    "universe_id": str(uuid.uuid4()),
                },
            )
            self.assertEqual(response.status_code, 302)
            self.db.dreamlight_character_skill.assert_called_with(
                self.character["id"], skill["id"]
            )
        self.client.post(self.character_path("skill"), data={"skill_id": ""})
        self.db.dreamlight_character_skill.assert_called_with(
            self.character["id"], None
        )
        self.db.dreamlight_character_skill.reset_mock()
        for invalid in ("bad", str(uuid.uuid4())):
            response = self.client.post(
                self.character_path("skill"), data={"skill_id": invalid}
            )
            self.assertEqual(response.status_code, 400)
        self.db.dreamlight_character_skill.assert_not_called()

    def test_skill_shows_as_text_with_pencil_until_edited(self) -> None:
        document = lxml.html.fromstring(self.client.get("/dreamlight").data)
        self.assertFalse(document.xpath("//select[@name='skill_id']"))
        # Each character's skill appears in a card for small screens and a table
        # row for wider screens
        for view in ("card", "row"):
            element_id = f"skill-{view}-{self.character['id']}"
            (display,) = document.xpath(f"//*[@id='{element_id}']")
            self.assertEqual(display.text_content().strip(), "Unassigned")
            (button,) = display.xpath(".//button[.//i[contains(@class, 'bi-pencil')]]")
            self.assertEqual(
                button.get("hx-get"), self.character_path(f"skill-form?view={view}")
            )
            self.assertEqual(button.get("hx-target"), f"#{element_id}")

            form = lxml.html.fromstring(
                self.client.get(self.character_path(f"skill-form?view={view}")).data
            )
            self.assertEqual(form.get("id"), element_id)
            self.assertEqual(
                form.get("hx-post"), self.character_path(f"skill?view={view}")
            )
            self.assertEqual(
                form.xpath(".//button[text()='Cancel']/@hx-get"),
                [self.character_path(f"skill?view={view}")],
            )
            self.assertEqual(
                form.xpath(".//select[@name='skill_id']/option[@selected]/text()"),
                ["Unassigned"],
            )

            cancel = lxml.html.fromstring(
                self.client.get(self.character_path(f"skill?view={view}")).data
            )
            self.assertEqual(cancel.get("id"), element_id)
            self.assertEqual(cancel.text_content().strip(), "Unassigned")
        unknown = lxml.html.fromstring(
            self.client.get(self.character_path("skill?view=nope")).data
        )
        self.assertEqual(unknown.get("id"), f"skill-row-{self.character['id']}")
        for path in ("skill", "skill-form"):
            self.assertEqual(
                self.client.get(
                    f"/dreamlight/characters/{uuid.uuid4()}/{path}"
                ).status_code,
                404,
            )

    def test_htmx_skill_save_refreshes_every_copy_and_totals(self) -> None:
        mining = self.lists["skill"][0]

        def save(character_id: uuid.UUID, skill_id: uuid.UUID | None) -> None:
            self.character.update(skill_id=skill_id, skill=mining["name"])

        self.db.dreamlight_character_skill.side_effect = save
        response = self.client.post(
            self.character_path("skill?view=card"),
            data={"skill_id": str(mining["id"])},
            headers={"HX-Request": "true"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["HX-Reswap"], "none")
        self.db.dreamlight_character_skill.assert_called_once_with(
            self.character["id"], mining["id"]
        )
        document = lxml.html.fromstring(f"<div>{response.data.decode()}</div>")
        for view in ("card", "row"):
            (display,) = document.xpath(
                f"//*[@id='skill-{view}-{self.character['id']}']"
            )
            self.assertEqual(display.get("hx-swap-oob"), "true")
            self.assertEqual(display.text_content().strip(), "Mining")
        (totals,) = document.xpath("//*[@id='skill-totals']")
        self.assertEqual(totals.get("hx-swap-oob"), "true")
        self.assertIn("Mining: 1", totals.text_content())
        self.assertIn("Unassigned: 0", totals.text_content())

        self.db.dreamlight_character_skill.reset_mock()
        response = self.client.post(
            self.character_path("skill?view=card"),
            data={"skill_id": "bad"},
            headers={"HX-Request": "true"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("HX-Reswap", response.headers)
        form = lxml.html.fromstring(response.data)
        self.assertEqual(form.get("id"), f"skill-card-{self.character['id']}")
        self.assertIn("Choose a valid Skill.", form.text_content())
        self.db.dreamlight_character_skill.assert_not_called()

    def test_cards_and_table_both_list_filtered_characters(self) -> None:
        document = lxml.html.fromstring(self.client.get("/dreamlight").data)
        (card,) = document.xpath("//div[contains(@class, 'card-body')]")
        self.assertEqual(card.xpath(".//h3/text()"), ["Mickey Mouse"])
        self.assertIn("Mickey & Friends · Plaza", card.text_content())
        # Delete forms keep the current filters in their query string
        for actions in (
            card.xpath(".//form/@action"),
            document.xpath("//tbody/tr/td//form/@action"),
        ):
            self.assertEqual(
                [a.split("?")[0] for a in actions], [self.character_path("delete")]
            )
        self.db.dreamlight_characters_list.return_value = []
        document = lxml.html.fromstring(self.client.get("/dreamlight").data)
        self.assertFalse(document.xpath("//div[contains(@class, 'card-body')]"))
        message = "Add Areas and Universes below, then add your first character."
        empty = document.xpath(f"//p[text()='{message}'] | //td[text()='{message}']")
        self.assertEqual([e.tag for e in empty], ["p", "td"])

    def test_delete_and_unknown_character_or_action(self) -> None:
        self.assertEqual(
            self.client.get(self.character_path("delete")).status_code, 405
        )
        self.assertEqual(
            self.client.post(self.character_path("delete")).status_code, 302
        )
        self.db.dreamlight_character_delete.assert_called_once_with(
            self.character["id"]
        )
        for path in (
            f"/dreamlight/characters/{uuid.uuid4()}/skill",
            self.character_path("edit"),
        ):
            self.assertEqual(self.client.post(path).status_code, 404)

    def test_combined_filters_and_global_totals_include_zero(self) -> None:
        mining = self.lists["skill"][0]["id"]
        self.db.dreamlight_characters_list.return_value += [
            self.character
            | {
                "id": uuid.uuid4(),
                "name": "Minnie Mouse",
                "skill_id": mining,
                "skill": "Mining",
            }
        ]
        query = {
            "name": "mINn",
            "area": str(self.character["area_id"]),
            "universe": str(self.character["universe_id"]),
            "skill": str(mining),
        }
        response = self.client.get("/dreamlight", query_string=query)
        document = lxml.html.fromstring(response.data)
        self.assertEqual(document.xpath("//tbody/tr/th/text()"), ["Minnie Mouse"])
        for total in (b"Mining: 1", b"Fishing: 0", b"Unassigned: 1", b"Showing 1 of 2"):
            self.assertIn(total, response.data)
        response = self.client.get("/dreamlight?skill=unassigned")
        self.assertEqual(
            lxml.html.fromstring(response.data).xpath("//tbody/tr/th/text()"),
            ["Mickey Mouse"],
        )
        response = self.client.get(
            "/dreamlight", query_string=query | {"area": str(uuid.uuid4())}
        )
        self.assertIn(b"Showing 0 of 2", response.data)
        response = self.client.post(
            self.character_path("skill"), query_string=query, data={"skill_id": ""}
        )
        self.assertIn("name=mINn", response.location)
        self.assertIn(f"skill={mining}", response.location)

    def test_lookup_crud_and_duplicate_validation(self) -> None:
        for kind in self.lists:
            with self.subTest(kind=kind):
                base = f"/dreamlight/lists/{kind}"
                self.assertEqual(
                    self.client.post(
                        f"{base}/add", data={"name": "  New  "}
                    ).status_code,
                    302,
                )
                self.db.dreamlight_lookup_save.assert_called_with(kind, "New", None)
                for name in (" ", self.lists[kind][0]["name"].upper()):
                    self.assertEqual(
                        self.client.post(
                            f"{base}/add", data={"name": name}
                        ).status_code,
                        400,
                    )
                unused = {"id": uuid.uuid4(), "name": "Unused"}
                self.lists[kind].append(unused)
                self.assertEqual(
                    self.client.post(
                        f"{base}/rename",
                        data={"id": str(unused["id"]), "name": "Renamed"},
                    ).status_code,
                    302,
                )
                self.db.dreamlight_lookup_save.assert_called_with(
                    kind, "Renamed", unused["id"]
                )
                self.assertEqual(
                    self.client.post(
                        f"{base}/delete", data={"id": str(unused["id"])}
                    ).status_code,
                    302,
                )
                self.db.dreamlight_lookup_delete.assert_called_with(kind, unused["id"])
        self.assertEqual(
            self.client.post("/dreamlight/lists/invalid/add").status_code, 404
        )
        self.assertEqual(
            self.client.post("/dreamlight/lists/area/invalid").status_code, 404
        )

    def test_referenced_lists_are_protected_but_skills_can_be_renamed(self) -> None:
        self.character["skill_id"] = self.lists["skill"][0]["id"]
        for kind in self.lists:
            entry_id = str(self.lists[kind][0]["id"])
            base = f"/dreamlight/lists/{kind}"
            self.assertEqual(
                self.client.post(f"{base}/delete", data={"id": entry_id}).status_code,
                400,
            )
            self.assertEqual(
                self.client.post(
                    f"{base}/rename", data={"id": entry_id, "name": "Renamed"}
                ).status_code,
                302 if kind == "skill" else 400,
            )
        self.db.dreamlight_lookup_delete.assert_not_called()
        self.db.dreamlight_lookup_save.assert_called_once_with(
            "skill", "Renamed", self.character["skill_id"]
        )

    def test_database_conflicts_return_validation_error(self) -> None:
        self.db.dreamlight_character_skill.side_effect = psycopg2.IntegrityError()
        self.assertEqual(
            self.client.post(
                self.character_path("skill"), data={"skill_id": ""}
            ).status_code,
            400,
        )

    def test_empty_state_and_escaping(self) -> None:
        self.character["name"] = "<script>alert(1)</script>"
        response = self.client.get("/dreamlight")
        self.assertNotIn(b"<script>alert(1)</script>", response.data)
        self.assertIn(b"&lt;script&gt;", response.data)
        self.db.dreamlight_characters_list.return_value = []
        for entries in self.lists.values():
            entries.clear()
        response = self.client.get("/dreamlight")
        self.assertIn(b"Unassigned: 0", response.data)
        document = lxml.html.fromstring(response.data)
        self.assertTrue(document.xpath("//button[text()='Add character']/@disabled"))

    def test_permissions_cover_reads_and_mutations(self) -> None:
        self.db.user_permissions_get.return_value = []
        for path in (
            "/dreamlight",
            "/dashboard-card/dreamlight",
            self.character_path("skill"),
            self.character_path("skill-form"),
        ):
            self.client.get(path)
        for path in (
            "/dreamlight/characters/add",
            self.character_path("skill"),
            self.character_path("delete"),
            "/dreamlight/lists/area/add",
            "/dreamlight/lists/universe/rename",
            "/dreamlight/lists/skill/delete",
        ):
            self.client.post(path)
        self.db.dreamlight_characters_list.assert_not_called()
        self.db.dreamlight_lookup_list.assert_not_called()
        self.db.dreamlight_character_add.assert_not_called()
        self.db.dreamlight_character_skill.assert_not_called()
        self.db.dreamlight_character_delete.assert_not_called()
        self.db.dreamlight_lookup_save.assert_not_called()
        self.db.dreamlight_lookup_delete.assert_not_called()
        self.db.user_permissions_get.return_value = ["admin"]
        self.assertEqual(self.client.get("/dreamlight").status_code, 200)


class DreamlightDatabaseTests(unittest.TestCase):
    def test_database_writes_only_skill_on_update_and_omits_skill_on_creation(
        self,
    ) -> None:
        db = object.__new__(YavinDatabase)
        with patch.object(db, "u") as execute:
            character_id, area_id, universe_id, skill_id = (
                uuid.uuid4() for _ in range(4)
            )
            db.dreamlight_character_add("Mickey", area_id, universe_id)
            sql, params = execute.call_args.args
            self.assertNotIn("skill_id", sql)
            self.assertEqual(
                params,
                {"name": "Mickey", "area_id": area_id, "universe_id": universe_id},
            )
            db.dreamlight_character_skill(character_id, skill_id)
            sql, params = execute.call_args.args
            self.assertNotIn("name=", sql)
            self.assertNotIn("area_id=", sql)
            self.assertNotIn("universe_id=", sql)
            self.assertEqual(params, {"id": character_id, "skill_id": skill_id})

    def test_lookup_table_allowlist(self) -> None:
        with self.assertRaises(KeyError):
            YavinDatabase.dreamlight_table("area; drop table users")


if __name__ == "__main__":
    unittest.main()
