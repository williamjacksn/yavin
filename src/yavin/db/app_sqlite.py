import datetime as dt
import decimal
import json
import logging
import sqlite3
import typing
import uuid
import zoneinfo

import yavin.util
from yavin.db.app import (
    BillboardRow,
    LibraryCredential,
    UserPermissions,
)

log = logging.getLogger(__name__)


def _register_adapters_and_converters() -> None:
    def convert_bool(value: bytes) -> bool:
        return value == b"True"

    sqlite3.register_adapter(bool, str)
    sqlite3.register_converter("bool", convert_bool)

    def convert_date(value: bytes) -> dt.date:
        return dt.date.fromisoformat(value.decode())

    sqlite3.register_adapter(dt.date, str)
    sqlite3.register_converter("date", convert_date)

    def convert_timestamp(value: bytes) -> dt.datetime:
        return dt.datetime.fromisoformat(value.decode())

    sqlite3.register_adapter(dt.datetime, str)
    sqlite3.register_converter("timestamp", convert_timestamp)

    def convert_decimal(value: bytes) -> decimal.Decimal:
        return decimal.Decimal(value.decode())

    sqlite3.register_adapter(decimal.Decimal, str)
    sqlite3.register_converter("decimal", convert_decimal)

    def convert_uuid(value: bytes) -> uuid.UUID:
        return uuid.UUID(value.decode())

    sqlite3.register_adapter(uuid.UUID, str)
    sqlite3.register_converter("uuid", convert_uuid)


_register_adapters_and_converters()


def connection_get(path: str) -> sqlite3.Connection:
    # Declared column types (date, decimal, uuid, ...) pick the converters above
    con = sqlite3.connect(path, autocommit=False, detect_types=sqlite3.PARSE_DECLTYPES)
    con.row_factory = sqlite3.Row
    con.execute("pragma busy_timeout=5000")
    return con


def connection_init(path: str) -> None:
    con = sqlite3.connect(path)
    con.execute("pragma journal_mode=wal")
    con.close()


def get_schema_version(con: sqlite3.Connection) -> int:
    if table_exists(con, "schema_versions"):
        sql = """
            select max(schema_version) current_version
            from schema_versions
        """
        for row in con.execute(sql):
            if row["current_version"] is not None:
                return int(row["current_version"])
    return 0


def migrate(con: sqlite3.Connection) -> None:
    current_version = get_schema_version(con)
    if current_version < 1:
        log.info("Migrating database to schema version 1")
        # Decimal columns are declared "decimal text" so values keep their
        # exact digits: the first word picks the decimal converter and "text"
        # stops SQLite from storing them as floating point numbers
        con.execute("""
            create table schema_versions (
                migration_timestamp timestamp,
                schema_version integer primary key
            )
        """)
        con.execute("""
            create table balances_accounts (
                account_name text,
                id uuid primary key
            )
        """)
        con.execute("""
            create table balances_transactions (
                account_id uuid,
                tx_date date,
                tx_description text,
                tx_id uuid primary key,
                tx_value decimal text
            )
        """)
        con.execute("""
            create table billboard_number_one (
                artist text,
                fetched_at timestamp,
                id uuid primary key,
                title text
            )
        """)
        con.execute("""
            create table callings (
                calling text,
                id uuid primary key,
                released_at date,
                set_apart_at date,
                sustained_at date,
                ward text
            )
        """)
        con.execute("""
            create table dreamlight_areas (
                id uuid primary key,
                name text
            )
        """)
        con.execute("""
            create table dreamlight_character_skill (
                character_id uuid,
                skill_id uuid,
                user_email text,
                primary key (character_id, user_email)
            )
        """)
        con.execute("""
            create table dreamlight_characters (
                area_id uuid,
                id uuid primary key,
                name text,
                universe_id uuid
            )
        """)
        con.execute("""
            create table dreamlight_skills (
                id uuid primary key,
                name text
            )
        """)
        con.execute("""
            create table dreamlight_universes (
                id uuid primary key,
                name text
            )
        """)
        con.execute("""
            create table electricity (
                bill decimal text,
                bill_date date primary key,
                charge decimal text,
                kwh integer
            )
        """)
        con.execute("""
            create table hymn_history (
                date date,
                hymn_number integer
            )
        """)
        con.execute("""
            create table hymn_tags (
                hymn_number integer,
                tag text,
                primary key (hymn_number, tag)
            )
        """)
        con.execute("""
            create table hymns (
                first_line text,
                hymn_number integer primary key,
                title text
            )
        """)
        con.execute("""
            create table jar_entries (
                entry_date date,
                id integer primary key,
                paid bool
            )
        """)
        con.execute("""
            create table library_books (
                credential_id uuid,
                due date,
                id uuid primary key,
                item_id text,
                medium text,
                renewable bool,
                title text
            )
        """)
        con.execute("""
            create table library_credentials (
                balance integer,
                display_name text,
                id uuid primary key,
                library text,
                library_type text,
                password text,
                username text
            )
        """)
        con.execute("""
            create table mileage_entries (
                entry_date date primary key,
                mileage integer
            )
        """)
        con.execute("""
            create table movie_people (
                id uuid primary key,
                person text
            )
        """)
        con.execute("""
            create table movie_picks (
                id uuid primary key,
                person_id uuid,
                pick_date date,
                pick_text text,
                pick_url text
            )
        """)
        con.execute("""
            create table phone_usage (
                end_date date,
                id uuid primary key,
                megabytes integer,
                messages integer,
                minutes integer,
                start_date date
            )
        """)
        con.execute("""
            create table settings (
                setting_id text primary key,
                setting_value text
            )
        """)
        con.execute("""
            create table tello_balances (
                allowance text,
                fetched_at timestamp,
                id uuid primary key,
                line text,
                percentage_available decimal text,
                remaining text,
                renewal_date date,
                subscription_id text
            )
        """)
        con.execute("""
            create table theatre_entries (
                company text,
                director text,
                first_show date,
                id uuid primary key,
                last_show date,
                performances integer,
                performer text,
                role text,
                show text
            )
        """)
        con.execute("""
            create table tithing_income (
                amount decimal text,
                date date,
                description text,
                id uuid primary key,
                tithing_paid date
            )
        """)
        con.execute("""
            create table user_permissions (
                email text primary key,
                permissions text
            )
        """)
        con.execute("""
            create table weight_entries (
                entry_date date primary key,
                weight decimal text
            )
        """)
        schema_versions_insert(con, 1)


def init(path: str) -> None:
    """Get the database ready at startup by bringing its schema up to date."""
    connection_init(path)
    con = connection_get(path)
    migrate(con)
    con.close()


def schema_versions_insert(con: sqlite3.Connection, schema_version: int) -> None:
    sql = """
        insert into schema_versions (schema_version, migration_timestamp)
        values (:schema_version, :migration_timestamp)
    """
    params = {
        "schema_version": schema_version,
        "migration_timestamp": dt.datetime.now(dt.UTC),
    }
    con.execute(sql, params)
    con.commit()


def table_exists(con: sqlite3.Connection, table_name: str) -> bool:
    sql = """
        select count(*) table_count
        from sqlite_master
        where type = 'table' and name = :table_name
    """
    params = {"table_name": table_name}
    for row in con.execute(sql, params):
        if row["table_count"] == 0:
            return False
    return True


class YavinSqliteDatabase:
    """The app's queries. Text is sorted with "collate nocase" so the ordering
    ignores case."""

    log = log

    def __init__(self, path: str) -> None:
        self.con = connection_get(path)

    def close(self) -> None:
        self.con.close()

    def serialize(self) -> bytes:
        """A consistent copy of the whole database file, including changes that are
        still in the write-ahead log."""
        return self.con.serialize()

    # query helpers

    def b(self, sql: str, records: list[dict]) -> None:
        """Batch execute a query"""
        self.con.executemany(sql, records)
        self.con.commit()

    def q(self, sql: str, params: dict | None = None) -> list[dict]:
        return [dict(row) for row in self.con.execute(sql, params or {})]

    def q_one(self, sql: str, params: dict | None = None) -> dict | None:
        row = self.con.execute(sql, params or {}).fetchone()
        return dict(row) if row else None

    def q_val(self, sql: str, params: dict | None = None) -> typing.Any:  # noqa: ANN401
        row = self.con.execute(sql, params or {}).fetchone()
        return row[0] if row else None

    def u(self, sql: str, params: dict | None = None) -> int:
        cursor = self.con.execute(sql, params or {})
        self.con.commit()
        return cursor.rowcount

    # Disney Dreamlight Valley

    @staticmethod
    def dreamlight_table(kind: str) -> str:
        return {
            "area": "dreamlight_areas",
            "universe": "dreamlight_universes",
            "skill": "dreamlight_skills",
        }[kind]

    def dreamlight_lookup_list(self, kind: str) -> list[dict]:
        table = self.dreamlight_table(kind)
        return self.q(f"select id, name from {table} order by lower(name), id")  # noqa: S608

    def dreamlight_lookup_save(
        self, kind: str, name: str, entry_id: uuid.UUID | None = None
    ) -> None:
        table = self.dreamlight_table(kind)
        if entry_id is None:
            self.u(
                f"insert into {table} (id, name) values (:id, :name)",  # noqa: S608
                {"id": uuid.uuid4(), "name": name},
            )
        else:
            self.u(
                f"update {table} set name = :name where id = :id",  # noqa: S608
                {"name": name, "id": entry_id},
            )

    def dreamlight_lookup_delete(self, kind: str, entry_id: uuid.UUID) -> None:
        table = self.dreamlight_table(kind)
        self.u(f"delete from {table} where id = :id", {"id": entry_id})  # noqa: S608

    def dreamlight_characters_list(self, user_email: str) -> list[dict]:
        """All characters, with the skills that user_email assigned to them."""
        return self.q(
            """
            select
                c.id, c.name, c.area_id, a.name as area, c.universe_id,
                u.name as universe, cs.skill_id, s.name as skill
            from dreamlight_characters c
            join dreamlight_areas a on a.id = c.area_id
            join dreamlight_universes u on u.id = c.universe_id
            left join dreamlight_character_skill cs
                on cs.character_id = c.id and cs.user_email = :user_email
            left join dreamlight_skills s on s.id = cs.skill_id
            order by lower(c.name), c.id
            """,
            {"user_email": user_email},
        )

    def dreamlight_skills_in_use(self) -> set[uuid.UUID]:
        """Skills that any user has assigned to a character."""
        rows = self.q("select distinct skill_id from dreamlight_character_skill")
        return {row["skill_id"] for row in rows}

    def dreamlight_characters_list_all(self) -> list[dict]:
        return self.q("""
            select area_id, id, name, universe_id
            from dreamlight_characters
        """)

    def dreamlight_character_skill_list_all(self) -> list[dict]:
        """Every user's skill assignments."""
        return self.q("""
            select character_id, skill_id, user_email
            from dreamlight_character_skill
        """)

    def dreamlight_character_add(
        self, name: str, area_id: uuid.UUID, universe_id: uuid.UUID
    ) -> None:
        self.u(
            """
            insert into dreamlight_characters (id, name, area_id, universe_id)
            values (:id, :name, :area_id, :universe_id)
            """,
            {
                "id": uuid.uuid4(),
                "name": name,
                "area_id": area_id,
                "universe_id": universe_id,
            },
        )

    def dreamlight_character_skill(
        self, character_id: uuid.UUID, user_email: str, skill_id: uuid.UUID | None
    ) -> None:
        """Set the skill user_email assigned to a character, or clear it if
        skill_id is None."""
        params = {
            "character_id": character_id,
            "user_email": user_email,
            "skill_id": skill_id,
        }
        if skill_id is None:
            self.u(
                """
                delete from dreamlight_character_skill
                where character_id = :character_id and user_email = :user_email
                """,
                params,
            )
        else:
            self.u(
                """
                insert into dreamlight_character_skill (
                    character_id, user_email, skill_id
                ) values (:character_id, :user_email, :skill_id)
                on conflict (character_id, user_email)
                do update set skill_id = excluded.skill_id
                """,
                params,
            )

    def dreamlight_character_delete(self, character_id: uuid.UUID) -> None:
        # Remove the skill assignments too, so none point at a missing character
        params = {"id": character_id}
        self.u(
            "delete from dreamlight_character_skill where character_id = :id", params
        )
        self.u("delete from dreamlight_characters where id = :id", params)

    # theatre

    def theatre_list(self) -> list[dict]:
        return self.q("""
            select * from theatre_entries
            order by
                first_show desc nulls first,
                show collate nocase,
                performer collate nocase,
                id
        """)

    def theatre_save(self, entry: dict, entry_id: uuid.UUID | None = None) -> None:
        params = {**entry, "id": entry_id or uuid.uuid4()}
        if entry_id is not None:
            self.u(
                """
                update theatre_entries set performer = :performer, show = :show,
                    first_show = :first_show, last_show = :last_show,
                    performances = :performances, role = :role,
                    company = :company, director = :director
                where id = :id
                """,
                params,
            )
        else:
            self.u(
                """
                insert into theatre_entries
                    (id, performer, show, first_show, last_show, performances,
                     role, company, director)
                values (:id, :performer, :show, :first_show, :last_show,
                        :performances, :role, :company, :director)
                """,
                params,
            )

    def theatre_import(self, entries: str) -> None:
        """Insert entries from a JSON list, skipping exact duplicates of existing
        entries and of each other."""
        fields = (
            "performer",
            "show",
            "first_show",
            "last_show",
            "performances",
            "role",
            "company",
            "director",
        )
        rows = dict.fromkeys(
            tuple(entry.get(f) for f in fields) for entry in json.loads(entries)
        )
        match = " and ".join(f"{f} is :{f}" for f in fields)
        for row in rows:
            params = dict(zip(fields, row, strict=True))
            if self.q_val(f"select 1 from theatre_entries where {match}", params):  # noqa: S608
                continue
            self.theatre_save(params)

    # balances

    def balances_accounts_count(self) -> int:
        return int(self.q_val("select count(*) from balances_accounts"))

    def balances_accounts_list(self) -> list[dict]:
        # Balances are added up here so decimal amounts stay exact
        accounts = self.q("""
            select id as account_id, account_name
            from balances_accounts
            order by account_name collate nocase
        """)
        totals: dict[uuid.UUID, decimal.Decimal] = {}
        for t in self.q("select account_id, tx_value from balances_transactions"):
            totals[t["account_id"]] = totals.get(t["account_id"], 0) + t["tx_value"]
        for a in accounts:
            a["account_balance"] = totals.get(a["account_id"], decimal.Decimal(0))
        return accounts

    def balances_transactions_add(self, params: dict) -> None:
        sql = """
            insert into balances_transactions (
                account_id, tx_date, tx_description, tx_id, tx_value
            ) values (
                :account_id, :tx_date, :tx_description, :tx_id, :tx_value
            )
        """
        self.u(sql, {**params, "tx_id": uuid.uuid4()})

    def balances_transactions_list(self, account_id: uuid.UUID) -> list[dict]:
        rows = self.q(
            """
            select
                a.id as account_id,
                a.account_name,
                t.tx_id,
                t.tx_date,
                t.tx_description,
                t.tx_value
            from balances_accounts a
            left join balances_transactions t on t.account_id = a.id
            where a.id = :account_id
            order by t.tx_date desc, t.tx_description collate nocase
            """,
            {"account_id": account_id},
        )
        balance = sum((r["tx_value"] or 0 for r in rows), decimal.Decimal(0))
        for r in rows:
            r["account_balance"] = balance
        return rows

    def balances_transactions_list_all(self) -> list[dict]:
        return self.q("""
            select account_id, tx_date, tx_description, tx_id, tx_value
            from balances_transactions
        """)

    # billboard

    def billboard_get_latest(self) -> BillboardRow:
        sql = """
            select artist, fetched_at, id, title
            from billboard_number_one
            order by fetched_at desc
            limit 1
        """
        return BillboardRow.from_dict(self.q_one(sql))

    def billboard_insert(self, artist: str, title: str) -> None:
        sql = """
            insert into billboard_number_one (artist, fetched_at, id, title)
            values (:artist, :fetched_at, :id, :title)
        """
        params = {
            "artist": artist,
            "fetched_at": dt.datetime.now(dt.UTC),
            "id": uuid.uuid4(),
            "title": title,
        }
        self.u(sql, params)

    def billboard_list_all(self) -> list[BillboardRow]:
        sql = """
            select artist, fetched_at, id, title
            from billboard_number_one
        """
        return [BillboardRow.from_dict(row) for row in self.q(sql)]

    def billboard_update_fetched_at(self, _id: uuid.UUID) -> None:
        sql = """
            update billboard_number_one
            set fetched_at = :fetched_at
            where id = :id
        """
        self.u(sql, {"fetched_at": dt.datetime.now(dt.UTC), "id": _id})

    # callings

    def callings_insert(self, params: dict) -> None:
        sql = """
            insert into callings (
                calling, id, released_at, set_apart_at, sustained_at, ward
            ) values (
                :calling, :id, :released_at, :set_apart_at, :sustained_at, :ward
            )
        """
        self.u(sql, {**params, "id": uuid.uuid4()})

    def callings_get(self, calling_id: uuid.UUID) -> dict | None:
        sql = """
            select id, ward, calling, sustained_at, set_apart_at, released_at
            from callings
            where id = :id
        """
        return self.q_one(sql, {"id": calling_id})

    def callings_update(self, params: dict) -> None:
        sql = """
            update callings
            set ward = :ward, calling = :calling,
                sustained_at = :sustained_at, set_apart_at = :set_apart_at,
                released_at = :released_at
            where id = :id
        """
        self.u(sql, params)

    def callings_list(self) -> list[dict]:
        sql = """
            select id, ward, calling, sustained_at, set_apart_at, released_at
            from callings
            order by sustained_at desc
        """
        return self.q(sql)

    # electricity

    def electricity_insert(
        self,
        bill_date: dt.date,
        kwh: int,
        charge: decimal.Decimal,
        bill: decimal.Decimal,
    ) -> None:
        sql = """
            insert into electricity (bill_date, kwh, charge, bill)
            values (:bill_date, :kwh, :charge, :bill)
        """
        params = {"bill_date": bill_date, "kwh": kwh, "charge": charge, "bill": bill}
        self.u(sql, params)

    def electricity_list(self) -> list[dict]:
        sql = """
            select
                bill_date,
                kwh,
                charge,
                bill,
                round(avg(kwh) over (
                    order by bill_date desc rows between current row and 11 following)
                ) avg_12_months
            from electricity
            order by bill_date desc
        """
        rows = self.q(sql)
        for r in rows:
            # Return the rounded average as a whole decimal number
            r["avg_12_months"] = decimal.Decimal(int(r["avg_12_months"]))
        return rows

    # hymns

    def hymn_history_list(self) -> list[dict]:
        return self.q("select date, hymn_number from hymn_history")

    def hymn_tags_list(self) -> list[dict]:
        return self.q("select hymn_number, tag from hymn_tags")

    def hymns_list(self) -> list[dict]:
        return self.q("select first_line, hymn_number, title from hymns")

    # jar

    def jar_entries_days_since_last(self) -> int:
        """Get the number of days since the last jar entry. If the last jar entry was
        today (or in the future), return 0. If there is no jar entry, return -1"""
        last_entry = self.q_val("select max(entry_date) from jar_entries")
        if last_entry is None:
            return -1
        # An aggregate has no declared type, so the date comes back as text
        last_entry = dt.date.fromisoformat(last_entry)
        today = self.today()
        if last_entry > today:
            return 0
        return (today - last_entry).days

    def jar_entries_insert(self, entry_date: dt.date) -> None:
        last: int | None = self.q_val("select max(id) from jar_entries")
        sql = """
            insert into jar_entries (entry_date, id, paid)
            values (:entry_date, :id, :paid)
        """
        params = {"entry_date": entry_date, "id": (last or 0) + 1, "paid": False}
        self.u(sql, params)

    def jar_entries_list_all(self) -> list[dict]:
        return self.q("select entry_date, id, paid from jar_entries")

    # library

    def library_credentials_delete(self, params: dict) -> None:
        self.u("delete from library_credentials where id = :id", params)

    def library_credentials_insert(self, params: dict) -> None:
        sql = """
            insert into library_credentials (
                balance, display_name, id, library, library_type, password,
                username
            ) values (
                0, :display_name, :id, :library, :library_type, :password,
                :username
            )
        """
        params.update({"id": uuid.uuid4()})
        self.u(sql, params)

    def library_credentials_list(self) -> list[LibraryCredential]:
        sql = """
            select id, library, username, password, display_name, balance, library_type
            from library_credentials
            order by display_name collate nocase
        """
        return typing.cast(list[LibraryCredential], self.q(sql))

    def library_books_count(self) -> dict:
        sql = """
            select
                count(*) books_count,
                coalesce(sum(due < :today), 0) overdue_count
            from library_books
        """
        return self.q_one(sql, {"today": self.today()}) or {}

    def library_books_insert(self, params: dict) -> None:
        sql = """
            insert into library_books (
                credential_id, due, id, item_id, medium, renewable, title
            ) values (
                :credential_id, :due, :id, :item_id, :medium, :renewable, :title
            )
        """
        params.update({"id": uuid.uuid4()})
        self.u(sql, params)

    def library_books_list(self) -> list[dict]:
        sql = """
            select c.display_name, b.title, b.due, b.renewable, b.item_id, b.medium
            from library_books b
            join library_credentials c on c.id = b.credential_id
            order by b.due, b.title collate nocase
        """
        return self.q(sql)

    def library_books_list_all(self) -> list[dict]:
        sql = """
            select credential_id, due, id, item_id, medium, renewable, title
            from library_books
        """
        return self.q(sql)

    def library_books_list_due(self) -> list[dict]:
        sql = """
            select b.title, b.due, b.medium, c.display_name account_name
            from library_books b
            join library_credentials c on c.id = b.credential_id
            where b.due <= :today
            order by c.display_name collate nocase, b.title collate nocase
        """
        return self.q(sql, {"today": self.today()})

    def library_books_truncate(self) -> None:
        self.u("delete from library_books")

    # mileage

    def mileage_entries_insert(self, entry_date: dt.date, mileage: int) -> None:
        sql = """
            insert into mileage_entries (entry_date, mileage)
            values (:entry_date, :mileage)
            on conflict (entry_date) do nothing
        """
        self.u(sql, {"entry_date": entry_date, "mileage": mileage})

    def mileage_entries_delete(self, entry_date: dt.date) -> None:
        sql = "delete from mileage_entries where entry_date = :entry_date"
        self.u(sql, {"entry_date": entry_date})

    def mileage_entries_list(self, limit: int = 100) -> list[dict]:
        sql = """
            select entry_date, mileage
            from mileage_entries
            order by entry_date desc
            limit :limit
        """
        return self.q(sql, {"limit": limit})

    def mileage_entries_get_for_date(self, entry_date: dt.date) -> dict | None:
        sql = """
            select entry_date, mileage
            from mileage_entries
            where entry_date = :entry_date
        """
        return self.q_one(sql, {"entry_date": entry_date})

    def mileage_entries_list_all(self) -> list[dict]:
        sql = """
            select entry_date, mileage
            from mileage_entries
            order by entry_date
        """
        return self.q(sql)

    # movie night

    def movie_people_insert(self, params: dict) -> None:
        params.update({"id": uuid.uuid4()})
        self.u("insert into movie_people (id, person) values (:id, :person)", params)

    def movie_people_list(self) -> list[dict]:
        sql = """
            select
                movie_people.id,
                person,
                row_number() over (
                    order by max(pick_date) nulls first, movie_people.id
                ) pick_order
            from movie_people
            left join movie_picks on movie_people.id = movie_picks.person_id
            group by person, movie_people.id
            order by person collate nocase, pick_order
        """
        return self.q(sql)

    def movie_people_next_pick(self) -> dict:
        sql = """
            with l as (
                select person_id, max(pick_date) last_pick_date
                from movie_picks
                group by person_id
            ), p as (
                select m.id, m.person, l.last_pick_date
                from movie_people m
                left join l on l.person_id = m.id
            )
            select id, person
            from p
            order by last_pick_date nulls first, id
            limit 1
        """
        return self.q_one(sql) or {}

    def movie_picks_delete(self, params: dict) -> None:
        self.u("delete from movie_picks where id = :id", params)

    def movie_picks_get(self, pick_id: uuid.UUID) -> dict | None:
        sql = """
            select id, person_id, pick_date, pick_text, pick_url
            from movie_picks
            where id = :id
        """
        return self.q_one(sql, {"id": pick_id})

    def movie_picks_insert(self, params: dict) -> None:
        sql = """
            insert into movie_picks (id, pick_date, person_id, pick_text, pick_url)
            values (:id, :pick_date, :person_id, :pick_text, :pick_url)
        """
        params.update({"id": uuid.uuid4()})
        if params.get("pick_url") == "":
            params.update({"pick_url": None})
        self.u(sql, params)

    def movie_picks_list(self) -> list[dict]:
        sql = """
            select movie_picks.id, pick_date, person_id, person, pick_text, pick_url
            from movie_picks
            join movie_people on movie_picks.person_id = movie_people.id
            order by pick_date desc, movie_picks.id
        """
        return self.q(sql)

    def movie_picks_update(self, params: dict) -> None:
        sql = """
            update movie_picks
            set pick_date = :pick_date, person_id = :person_id,
                pick_text = :pick_text, pick_url = :pick_url
            where id = :id
        """
        if params.get("pick_url") == "":
            params.update({"pick_url": None})
        self.u(sql, params)

    # phone usage

    def phone_usage_insert(
        self,
        start_date: dt.date,
        end_date: dt.date,
        minutes: int,
        messages: int,
        megabytes: int,
    ) -> None:
        sql = """
            insert into phone_usage (
                end_date, id, megabytes, messages, minutes, start_date
            ) values (
                :end_date, :id, :megabytes, :messages, :minutes, :start_date
            )
        """
        params = {
            "end_date": end_date,
            "id": uuid.uuid4(),
            "megabytes": megabytes,
            "messages": messages,
            "minutes": minutes,
            "start_date": start_date,
        }
        self.u(sql, params)

    def phone_usage_list(self) -> list[dict]:
        sql = """
            select id, start_date, end_date, minutes, messages, megabytes
            from phone_usage
            order by end_date desc
        """
        return self.q(sql)

    # settings

    def display_time_zone(self) -> zoneinfo.ZoneInfo:
        """Return the display time zone from the settings table, or the default if
        the setting is missing or invalid."""
        sql = """
            select setting_value from settings
            where setting_id = 'display_time_zone'
        """
        return zoneinfo.ZoneInfo(yavin.util.valid_time_zone_name(self.q_val(sql)))

    def today(self) -> dt.date:
        """Return the current date in the display time zone."""
        return yavin.util.today(self.display_time_zone())

    def settings_delete(self, setting_id: str) -> None:
        sql = "delete from settings where setting_id = :setting_id"
        self.u(sql, {"setting_id": setting_id})

    def settings_list(self) -> dict[str, str]:
        rows = self.q("select setting_id, setting_value from settings")
        return {s.get("setting_id", ""): s.get("setting_value", "") for s in rows}

    def settings_update(self, setting_id: str, setting_value: str) -> None:
        sql = """
            insert into settings (setting_id, setting_value)
            values (:setting_id, :setting_value)
            on conflict (setting_id) do update set setting_value = :setting_value
        """
        self.u(sql, {"setting_id": setting_id, "setting_value": setting_value})

    # tello

    def tello_balances_insert(self, params: dict) -> None:
        sql = """
            insert into tello_balances (
                allowance, fetched_at, id, line, percentage_available, remaining,
                renewal_date, subscription_id
            ) values (
                :allowance, :fetched_at, :id, :line, :percentage_available,
                :remaining, :renewal_date, :subscription_id
            )
        """
        self.u(sql, {**params, "id": uuid.uuid4()})

    def tello_balances_list_latest(self) -> list[dict]:
        sql = """
            select
                allowance, fetched_at, line, percentage_available, remaining,
                renewal_date, subscription_id
            from tello_balances
            where fetched_at = (select max(fetched_at) from tello_balances)
            order by line collate nocase
        """
        return self.q(sql)

    def tello_balances_list_all(self) -> list[dict]:
        sql = """
            select
                allowance, fetched_at, id, line, percentage_available, remaining,
                renewal_date, subscription_id
            from tello_balances
        """
        return self.q(sql)

    def tello_balances_list_for_subscription(self, subscription_id: str) -> list[dict]:
        sql = """
            select
                allowance, fetched_at, line, percentage_available, remaining,
                renewal_date, subscription_id
            from tello_balances
            where subscription_id = :subscription_id
            order by fetched_at
        """
        return self.q(sql, {"subscription_id": subscription_id})

    # tithing

    def tithing_get_current_owed(self) -> decimal.Decimal:
        # Added up here so the decimal amounts stay exact, then rounded half up to
        # cents
        unpaid = self.q("select amount from tithing_income where tithing_paid is null")
        total = sum((r["amount"] for r in unpaid), decimal.Decimal(0))
        return (total * decimal.Decimal("0.1")).quantize(
            decimal.Decimal("0.01"), rounding=decimal.ROUND_HALF_UP
        )

    def tithing_income_insert(
        self, date: dt.date, amount: decimal.Decimal, description: str
    ) -> None:
        sql = """
            insert into tithing_income (amount, date, description, id)
            values (:amount, :date, :description, :id)
        """
        params = {
            "amount": amount,
            "date": date,
            "description": description,
            "id": uuid.uuid4(),
        }
        self.u(sql, params)

    def tithing_income_list_all(self) -> list[dict]:
        sql = """
            select amount, date, description, id, tithing_paid
            from tithing_income
        """
        return self.q(sql)

    def tithing_income_list_unpaid(self) -> list[dict]:
        sql = """
            select id, date, amount, description
            from tithing_income
            where tithing_paid is null
            order by date, description collate nocase, id
        """
        return self.q(sql)

    def tithing_income_mark_paid(self) -> None:
        sql = """
            update tithing_income
            set tithing_paid = :today
            where tithing_paid is null
        """
        self.u(sql, {"today": self.today()})

    # user permissions

    def user_permissions_add(self, email: str, permission: str) -> None:
        existing_permissions = self.user_permissions_get(email)
        if permission in existing_permissions:
            self.log.debug(f"{email} already has permission {permission}")
            return
        self.user_permissions_set(email, [*existing_permissions, permission])

    def user_permissions_delete(self, email: str) -> None:
        self.u("delete from user_permissions where email = :email", {"email": email})

    def user_permissions_get(self, email: str) -> list[str]:
        sql = "select permissions from user_permissions where email = :email"
        permissions = self.q_val(sql, {"email": email})
        if permissions:
            return sorted(set(permissions.split()))
        return []

    def user_permissions_list(self) -> list[UserPermissions]:
        sql = """
            select email, permissions
            from user_permissions
            order by email collate nocase
        """
        return [UserPermissions(r["email"], r["permissions"]) for r in self.q(sql)]

    def user_permissions_set(self, email: str, permissions: list[str]) -> None:
        sql = """
            insert into user_permissions (email, permissions)
            values (:email, :permissions)
            on conflict (email) do update set permissions = :permissions
        """
        params = {"email": email, "permissions": " ".join(sorted(set(permissions)))}
        self.u(sql, params)

    # weight

    def weight_entries_get_for_date(
        self, entry_date: dt.date
    ) -> decimal.Decimal | None:
        # This returns the first column, the date, not the weight
        sql = """
            select entry_date, weight
            from weight_entries
            where entry_date = :entry_date
        """
        return self.q_val(sql, {"entry_date": entry_date})

    def weight_entries_get_most_recent(self) -> dict | None:
        sql = """
            select entry_date, weight
            from weight_entries
            order by entry_date desc
            limit 1
        """
        return self.q_one(sql)

    def weight_entries_insert(
        self, entry_date: dt.date, weight: decimal.Decimal
    ) -> None:
        sql = """
            insert into weight_entries (entry_date, weight)
            values (:entry_date, :weight)
            on conflict (entry_date) do nothing
        """
        self.u(sql, {"entry_date": entry_date, "weight": weight})

    def weight_entries_list(self, limit: int = 10) -> list[dict]:
        sql = """
            select entry_date, weight
            from weight_entries
            order by entry_date desc
            limit :limit
        """
        return self.q(sql, {"limit": limit})

    def weight_entries_list_all(self) -> list[dict]:
        return self.q("select entry_date, weight from weight_entries")
