import json
import pathlib

package_json = pathlib.Path().resolve() / "package.json"
with package_json.open() as f:
    data = json.load(f)

bi: str = data.get("dependencies").get("bootstrap-icons")
bs: str = data.get("dependencies").get("bootstrap")
hx: str = data.get("dependencies").get("htmx.org")

app_version = "2024.8"
