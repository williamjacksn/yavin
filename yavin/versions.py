import json
import pathlib

data = json.loads(pathlib.Path("package.json").read_text())

bi: str = data.get("dependencies").get("bootstrap-icons")
bs: str = data.get("dependencies").get("bootstrap")
hx: str = data.get("dependencies").get("htmx.org")

app_version = "2024.8"
