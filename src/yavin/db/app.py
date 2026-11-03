import dataclasses
import datetime as dt
import uuid
from typing import TypedDict

DEFAULT_UUID = uuid.UUID(int=0)
DEFAULT_DATETIME = dt.datetime(1970, 1, 1, tzinfo=dt.UTC)


@dataclasses.dataclass
class BillboardRow:
    artist: str = ""
    fetched_at: dt.datetime = DEFAULT_DATETIME
    id: uuid.UUID = DEFAULT_UUID
    title: str = ""

    @classmethod
    def from_dict(cls, d: dict | None) -> BillboardRow:
        if d:
            return cls(d["artist"], d["fetched_at"], d["id"], d["title"])
        return cls()

    def __bool__(self) -> bool:
        return bool(self.artist)


class LibraryCredential(TypedDict):
    balance: int
    display_name: str
    id: uuid.UUID
    library: str
    library_type: str
    password: str
    username: str


@dataclasses.dataclass
class UserPermissions:
    email: str
    permissions_db: str

    @property
    def permissions(self) -> list[str]:
        return sorted(set(self.permissions_db.split()))
