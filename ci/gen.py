import json
import pathlib

ACTIONS_CHECKOUT = {"name": "Check out repository", "uses": "actions/checkout@v5"}
CONTAINER_IMAGE = "ghcr.io/williamjacksn/yavin"
DEFAULT_BRANCH = "master"
PUSH_OR_DISPATCH = (
    "github.event_name == 'push' || github.event_name == 'workflow_dispatch'"
)
THIS_FILE = pathlib.PurePosixPath(
    pathlib.Path(__file__).relative_to(pathlib.Path.cwd())
)


def gen(content: dict, target: str) -> None:
    pathlib.Path(target).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(target).write_text(
        json.dumps(content, indent=2, sort_keys=True), newline="\n"
    )


def gen_compose() -> None:
    target = "compose.yaml"
    description = f"This file ({target}) was generated from {THIS_FILE}"
    content = {
        "services": {
            "app": {
                "environment": {
                    "ADMIN_EMAIL": "(set in compose.override.yaml)",
                    "DESCRIPTION": description,
                    "DSN": "postgres://postgres:postgres@postgres/postgres",
                    "OPENID_CLIENT_ID": "(set in compose.override.yaml)",
                    "OPENID_CLIENT_SECRET": "(set in compose.override.yaml)",
                    "PORT": 8080,
                    "SECRET_KEY": "(set in compose.override.yaml)",
                    "SERVER_NAME": "localhost:8080",
                },
                "image": CONTAINER_IMAGE,
                "init": True,
                "ports": ["8080:8080"],
            },
            "postgres": {
                "image": "postgres:16",
                "environment": {
                    "POSTGRES_PASSWORD": "postgres",
                    "PGDATA": "/var/lib/postgresql/data/16",
                },
                "ports": ["5432:5432"],
                "volumes": ["postgres-data:/var/lib/postgresql/data"],
            },
            "shell": {
                "entrypoint": ["/bin/bash"],
                "image": CONTAINER_IMAGE,
                "init": True,
                "volumes": ["./:/app"],
            },
        },
        "volumes": {
            "postgres-data": {},
        },
    }
    gen(content, target)


def gen_dependabot() -> None:
    target = ".github/dependabot.yaml"
    content = {
        "version": 2,
        "updates": [
            {
                "package-ecosystem": e,
                "allow": [{"dependency-type": "all"}],
                "directory": "/",
                "schedule": {"interval": "daily"},
            }
            for e in ["docker", "docker-compose", "github-actions", "npm", "uv"]
        ],
    }
    gen(content, target)


def gen_deploy_workflow() -> None:
    target = ".github/workflows/build-and-deploy.yaml"
    content = {
        "env": {
            "description": f"This workflow ({target}) was generated from {THIS_FILE}"
        },
        "name": "Build and deploy app",
        "on": {
            "pull_request": {"branches": [DEFAULT_BRANCH]},
            "push": {"branches": [DEFAULT_BRANCH]},
            "workflow_dispatch": {},
        },
        "permissions": {},
        "jobs": {
            "build": {
                "name": "Build the container image",
                "permissions": {"packages": "write"},
                "runs-on": "ubuntu-latest",
                "steps": [
                    {
                        "name": "Set up Docker Buildx",
                        "uses": "docker/setup-buildx-action@v3",
                    },
                    {
                        "name": "Build the container image",
                        "uses": "docker/build-push-action@v6",
                        "with": {
                            "cache-from": "type=gha",
                            "cache-to": "type=gha,mode=max",
                            "tags": f"{CONTAINER_IMAGE}:latest",
                        },
                    },
                    {
                        "name": "Log in to GitHub container registry",
                        "if": PUSH_OR_DISPATCH,
                        "uses": "docker/login-action@v3",
                        "with": {
                            "password": "${{ github.token }}",
                            "registry": "ghcr.io",
                            "username": "${{ github.actor }}",
                        },
                    },
                    {
                        "name": "Push latest image to registry",
                        "if": PUSH_OR_DISPATCH,
                        "uses": "docker/build-push-action@v6",
                        "with": {
                            "cache-from": "type=gha",
                            "push": True,
                            "tags": f"{CONTAINER_IMAGE}:latest",
                        },
                    },
                ],
            },
            "deploy": {
                "name": "Deploy the app",
                "needs": "build",
                "if": PUSH_OR_DISPATCH,
                "runs-on": "ubuntu-latest",
                "steps": [
                    ACTIONS_CHECKOUT,
                    {
                        "name": "Deploy the app",
                        "run": "sh ci/ssh-deploy.sh",
                        "env": {
                            "SSH_HOST": "${{ secrets.ssh_host }}",
                            "SSH_PRIVATE_KEY": "${{ secrets.ssh_private_key }}",
                            "SSH_USER": "${{ secrets.ssh_user }}",
                        },
                    },
                ],
            },
        },
    }
    gen(content, target)


def gen_package_json() -> None:
    target = "package.json"
    content = {
        "description": f"This file ({target}) was generated from {THIS_FILE}",
        "name": "yavin",
        "version": "1.0.0",
        "license": "UNLICENSED",
        "private": True,
        "dependencies": {
            "bootstrap": "5.3.8",
            "bootstrap-icons": "1.13.1",
            "htmx.org": "2.0.7",
        },
    }
    gen(content, target)


def gen_ruff_workflow() -> None:
    target = ".github/workflows/ruff.yaml"
    content = {
        "name": "Ruff",
        "on": {
            "pull_request": {"branches": [DEFAULT_BRANCH]},
            "push": {"branches": [DEFAULT_BRANCH]},
        },
        "permissions": {"contents": "read"},
        "env": {
            "description": f"This workflow ({target}) was generated from {THIS_FILE}"
        },
        "jobs": {
            "ruff-check": {
                "name": "Run ruff check",
                "runs-on": "ubuntu-latest",
                "steps": [
                    ACTIONS_CHECKOUT,
                    {"name": "Run ruff check", "run": "sh ci/ruff-check.sh"},
                ],
            },
            "ruff-format": {
                "name": "Run ruff format",
                "runs-on": "ubuntu-latest",
                "steps": [
                    ACTIONS_CHECKOUT,
                    {"name": "Run ruff format", "run": "sh ci/ruff-format.sh"},
                ],
            },
        },
    }
    gen(content, target)


def main() -> None:
    gen_compose()
    gen_dependabot()
    gen_deploy_workflow()
    gen_package_json()
    gen_ruff_workflow()


if __name__ == "__main__":
    main()
