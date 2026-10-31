import os
import tempfile
import unittest
import uuid
from unittest.mock import MagicMock, patch

import lxml.html
from flask.sessions import SecureCookieSessionInterface

with (
    tempfile.TemporaryDirectory() as directory,
    patch.dict(os.environ, {"DATABASE": os.path.join(directory, "test.db")}),
):
    from yavin.app import app

from yavin.db.app import UserPermissions

ADMIN = "admin@example.com"
PLAYER = "player@example.com"
HTMX = {"HX-Request": "true"}


class UserPermissionsTests(unittest.TestCase):
    def setUp(self) -> None:
        # An in-memory stand-in for the user_permissions table
        self.store = {ADMIN: "admin", PLAYER: "dreamlight retired-page"}
        self.db = MagicMock()
        self.db.settings_list.return_value = {}
        self.db.user_permissions_get.side_effect = lambda email: sorted(
            self.store.get(email, "").split()
        )
        self.db.user_permissions_list.side_effect = lambda: [
            UserPermissions(email, permissions)
            for email, permissions in sorted(self.store.items())
        ]
        self.db.user_permissions_set.side_effect = lambda email, permissions: (
            self.store.update({email: " ".join(permissions)})
        )
        self.db.user_permissions_delete.side_effect = self.store.pop
        patcher = patch("yavin.db.YavinDatabase", return_value=self.db)
        patcher.start()
        self.addCleanup(patcher.stop)
        app.config.update(TESTING=True, SECRET_KEY=uuid.uuid4().hex)
        self.client = app.test_client()
        self.sign_in(ADMIN)

    def sign_in(self, email: str) -> None:
        serializer = SecureCookieSessionInterface().get_signing_serializer(app)
        if serializer is None:
            self.fail("The app has no secret key for signing sessions")
        self.client.set_cookie(
            app.config["SESSION_COOKIE_NAME"], serializer.dumps({"email": email})
        )

    def modal(self, query: str = "") -> lxml.html.HtmlElement:
        response = self.client.get(f"/user-permissions/modal{query}")
        self.assertEqual(response.status_code, 200)
        return lxml.html.fromstring(response.data)

    def assert_saved(self, path: str, data: dict) -> None:
        """A successful htmx save reloads the page instead of swapping content."""
        response = self.client.post(path, data=data, headers=HTMX)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("HX-Redirect"), "/user-permissions")

    def rejected(self, path: str, data: dict) -> lxml.html.HtmlElement:
        """A rejected htmx save returns the modal content with the error."""
        response = self.client.post(path, data=data, headers=HTMX)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("HX-Redirect", response.headers)
        return lxml.html.fromstring(response.data)

    def test_page_has_buttons_that_load_the_modal(self) -> None:
        document = lxml.html.fromstring(self.client.get("/user-permissions").data)
        self.assertTrue(document.xpath("//div[@id='modal-user-permissions']"))
        self.assertFalse(document.xpath("//form"))
        modal = "[@data-bs-target='#modal-user-permissions']"
        self.assertEqual(
            document.xpath(f"//button{modal}[contains(., 'Add user')]/@hx-get"),
            ["/user-permissions/modal"],
        )
        # Users are listed as cards on small screens and as table rows on wider
        # screens, each with its own edit button
        cards = document.xpath("//div[contains(@class, 'card-body')]")
        rows = document.xpath("//tbody/tr")
        for users in (cards, rows):
            self.assertEqual(
                [u.xpath("string((.//h5 | ./td)[1])") for u in users], [ADMIN, PLAYER]
            )
            self.assertEqual(
                [u.xpath(f"string(.//button{modal}/@hx-get)") for u in users],
                [
                    f"/user-permissions/modal?email={ADMIN}",
                    f"/user-permissions/modal?email={PLAYER}",
                ],
            )
        self.assertEqual(
            [c.strip() for c in cards[1].xpath(".//code/text()")],
            ["dreamlight", "retired-page"],
        )
        for button in document.xpath(f"//button{modal}"):
            self.assertEqual(button.get("hx-target"), "#modal-user-permissions-dialog")

    def test_edit_modal_checks_current_permissions_and_keeps_unknown_ones(
        self,
    ) -> None:
        form = self.modal(f"?email={PLAYER}")
        self.assertEqual(form.get("hx-post"), "/user-permissions/update")
        self.assertEqual(form.xpath("//input[@name='email']/@value"), [PLAYER])
        self.assertEqual(form.xpath("//input[@name='email']/@type"), ["hidden"])
        checked = form.xpath("//input[@name='permission'][@checked]/@value")
        self.assertEqual(sorted(checked), ["dreamlight", "retired-page"])
        choices = form.xpath("//input[@name='permission']/@value")
        for permission in ("admin", "callings", "dreamlight", "tello", "theatre"):
            self.assertIn(permission, choices)
        self.assertEqual(
            self.client.get("/user-permissions/modal?email=nobody@x").status_code, 404
        )

    def test_add_modal_asks_for_an_email(self) -> None:
        form = self.modal()
        self.assertEqual(form.get("hx-post"), "/user-permissions/add")
        self.assertEqual(form.xpath("//input[@name='email']/@type"), ["email"])
        self.assertFalse(form.xpath("//input[@name='permission'][@checked]"))
        self.assertNotIn(
            "retired-page", form.xpath("//input[@name='permission']/@value")
        )

    def test_save_sets_known_permissions_and_reloads(self) -> None:
        self.assert_saved(
            "/user-permissions/update",
            {
                "email": PLAYER,
                "permission": ["tello", "retired-page", "made-up", "callings"],
            },
        )
        self.db.user_permissions_set.assert_called_once_with(
            PLAYER, ["callings", "retired-page", "tello"]
        )

    def test_unchecking_everything_removes_the_user(self) -> None:
        self.assert_saved("/user-permissions/update", {"email": PLAYER})
        self.db.user_permissions_delete.assert_called_once_with(PLAYER)
        self.assertNotIn(PLAYER, self.store)

    def test_admins_cannot_remove_their_own_admin_permission(self) -> None:
        form = self.rejected(
            "/user-permissions/update", {"email": ADMIN, "permission": ["tello"]}
        )
        self.assertIn(
            "You can't remove your own admin permission.", form.text_content()
        )
        # What was checked stays checked so the admin can fix it
        self.assertEqual(
            form.xpath("//input[@name='permission'][@checked]/@value"), ["tello"]
        )
        self.db.user_permissions_set.assert_not_called()
        self.db.user_permissions_delete.assert_not_called()

    def test_add_user_validates_in_the_modal_and_saves(self) -> None:
        for data, message in (
            ({"email": "not-an-email", "permission": "tello"}, "valid email"),
            ({"email": "new@example.com"}, "at least one permission"),
            ({"email": PLAYER, "permission": "tello"}, "already has permissions"),
        ):
            with self.subTest(data=data):
                form = self.rejected("/user-permissions/add", data)
                self.assertIn(message, form.text_content())
                self.assertEqual(
                    form.xpath("//input[@name='email']/@value"), [data["email"]]
                )
        self.db.user_permissions_set.assert_not_called()
        self.assert_saved(
            "/user-permissions/add",
            {"email": " new@example.com ", "permission": ["tello", "made-up"]},
        )
        self.db.user_permissions_set.assert_called_once_with(
            "new@example.com", ["tello"]
        )

    def test_errors_are_flashed_when_posted_without_htmx(self) -> None:
        response = self.client.post(
            "/user-permissions/add",
            data={"email": "not-an-email", "permission": "tello"},
            follow_redirects=True,
        )
        document = lxml.html.fromstring(response.data)
        self.assertIn(
            "Enter a valid email address.",
            document.xpath("string(//div[contains(@class, 'alert-danger')])"),
        )

    def test_only_admins_can_view_or_change_permissions(self) -> None:
        self.sign_in(PLAYER)
        for path in (
            "/user-permissions",
            "/user-permissions/modal",
            f"/user-permissions/modal?email={PLAYER}",
        ):
            self.assertIn(b"not authorized", self.client.get(path).data.lower())
        for path in ("/user-permissions/update", "/user-permissions/add"):
            self.client.post(
                path,
                data={"email": PLAYER, "permission": ["admin", "dreamlight"]},
                headers=HTMX,
            )
        self.db.user_permissions_set.assert_not_called()
        self.db.user_permissions_delete.assert_not_called()


if __name__ == "__main__":
    unittest.main()
