import datetime
import decimal
import logging
import sqlite3
import uuid

log = logging.getLogger(__name__)


def _register_adapters_and_converters() -> None:
    def convert_bool(value: bytes) -> bool:
        return value == b"True"

    sqlite3.register_adapter(bool, str)
    sqlite3.register_converter("bool", convert_bool)

    def convert_date(value: bytes) -> datetime.date:
        return datetime.date.fromisoformat(value.decode())

    sqlite3.register_adapter(datetime.date, str)
    sqlite3.register_converter("date", convert_date)

    def convert_decimal(value: bytes) -> decimal.Decimal:
        return decimal.Decimal(value.decode())

    sqlite3.register_adapter(decimal.Decimal, str)
    sqlite3.register_converter("decimal", convert_decimal)

    def convert_uuid(value: bytes) -> uuid.UUID:
        return uuid.UUID(value.decode())

    sqlite3.register_adapter(uuid.UUID, str)
    sqlite3.register_converter("uuid", convert_uuid)


_register_adapters_and_converters()


def balances_accounts_insert(
    con: sqlite3.Connection, account_name: str, id: uuid.UUID
) -> None:
    sql = """
        insert into balances_accounts (account_name, id)
        values (:account_name, :id)
    """
    params = {
        "account_name": account_name,
        "id": id,
    }
    con.execute(sql, params)
    con.commit()


def balances_transactions_insert(
    con: sqlite3.Connection,
    account_id: uuid.UUID,
    tx_date: datetime.date,
    tx_description: str,
    tx_id: uuid.UUID,
    tx_value: decimal.Decimal,
) -> None:
    sql = """
        insert into balances_transactions (
            account_id, tx_date, tx_description, tx_id, tx_value
        ) values (
            :account_id, :tx_date, :tx_description, :tx_id, :tx_value
        )
    """
    params = {
        "account_id": account_id,
        "tx_date": tx_date,
        "tx_description": tx_description,
        "tx_id": tx_id,
        "tx_value": tx_value,
    }
    con.execute(sql, params)
    con.commit()


def billboard_insert(
    con: sqlite3.Connection,
    artist: str,
    fetched_at: datetime.datetime,
    id_: uuid.UUID,
    title: str,
) -> None:
    sql = """
        insert into billboard_number_one (
            artist, fetched_at, id, title
        ) values (
            :artist, :fetched_at, :id, :title
        )
    """
    params = {
        "artist": artist,
        "fetched_at": fetched_at,
        "id": id_,
        "title": title,
    }
    con.execute(sql, params)
    con.commit()


def callings_insert(
    con: sqlite3.Connection,
    calling: str,
    id_: uuid.UUID,
    released_at: datetime.date,
    set_apart_at: datetime.date,
    sustained_at: datetime.date,
    ward: str,
) -> None:
    sql = """
        insert into callings (
            calling, id, released_at, set_apart_at, sustained_at, ward
        ) values (
            :calling, :id, :released_at, :set_apart_at, :sustained_at, :ward
        )
    """
    params = {
        "calling": calling,
        "id": id_,
        "released_at": released_at,
        "set_apart_at": set_apart_at,
        "sustained_at": sustained_at,
        "ward": ward,
    }
    con.execute(sql, params)
    con.commit()


def connection_get(path: str) -> sqlite3.Connection:
    con = sqlite3.connect(path, autocommit=False)
    con.row_factory = sqlite3.Row
    con.execute("pragma busy_timeout=5000")
    return con


def connection_init(path: str) -> None:
    con = sqlite3.connect(path)
    con.execute("pragma journal_mode=wal")
    con.close()


def electricity_insert(
    con: sqlite3.Connection,
    bill: decimal.Decimal,
    bill_date: datetime.date,
    charge: decimal.Decimal,
    kwh: int,
) -> None:
    sql = """
        insert into electricity (
            bill, bill_date, charge, kwh
        ) values (
            :bill, :bill_date, :charge, :kwh
        )
    """
    params = {
        "bill": bill,
        "bill_date": bill_date,
        "charge": charge,
        "kwh": kwh,
    }
    con.execute(sql, params)
    con.commit()


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


def hymn_history_insert(
    con: sqlite3.Connection, date: datetime.date, hymn_number: int
) -> None:
    sql = """
        insert into hymn_history (date, hymn_number) values (:date, :hymn_number)
    """
    params = {"date": date, "hymn_number": hymn_number}
    con.execute(sql, params)
    con.commit()


def hymn_tags_insert(con: sqlite3.Connection, hymn_number: int, tag: str) -> None:
    sql = """
        insert into hymn_tags (hymn_number, tag) values (:hymn_number, :tag)
    """
    params = {"hymn_number": hymn_number, "tag": tag}
    con.execute(sql, params)
    con.commit()


def hymns_insert(
    con: sqlite3.Connection, first_line: str, hymn_number: int, title: str
) -> None:
    sql = """
        insert into hymns (
            first_line, hymn_number, title
        ) values (
            :first_line, :hymn_number, :title
        )
    """
    params = {"first_line": first_line, "hymn_number": hymn_number, "title": title}
    con.execute(sql, params)
    con.commit()


def jar_entries_insert(
    con: sqlite3.Connection, entry_date: datetime.date, id_: int, paid: bool
) -> None:
    sql = """
        insert into jar_entries (entry_date, id, paid) values (:entry_date, :id, :paid)
    """
    params = {"entry_date": entry_date, "id": id_, "paid": paid}
    con.execute(sql, params)
    con.commit()


def library_books_insert(
    con: sqlite3.Connection,
    credential_id: uuid.UUID,
    due: datetime.date,
    id_: uuid.UUID,
    item_id: str,
    medium: str,
    renewable: bool,
    title: str,
) -> None:
    sql = """
        insert into library_books (
            credential_id, due, id, item_id, medium, renewable, title
        ) values (
            :credential_id, :due, :id, :item_id, :medium, :renewable, :title
        )
    """
    params = {
        "credential_id": credential_id,
        "due": due,
        "id": id_,
        "item_id": item_id,
        "medium": medium,
        "renewable": renewable,
        "title": title,
    }
    con.execute(sql, params)
    con.commit()


def library_credentials_insert(
    con: sqlite3.Connection,
    balance: int,
    display_name: str,
    id_: uuid.UUID,
    library: str,
    library_type: str,
    password: str,
    username: str,
) -> None:
    sql = """
        insert into library_credentials (
            balance, display_name, id, library, library_type, password, username
        ) values (
            :balance, :display_name, :id, :library, :library_type, :password, :username
        )
    """
    params = {
        "balance": balance,
        "display_name": display_name,
        "id": id_,
        "library": library,
        "library_type": library_type,
        "password": password,
        "username": username,
    }
    con.execute(sql, params)
    con.commit()


def migrate(con: sqlite3.Connection) -> None:
    current_version = get_schema_version(con)
    if current_version < 1:
        log.info("Migrating database to schema version 1")
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
                tx_value decimal
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
            create table captains_log (
                id uuid primary key,
                log_text text,
                log_timestamp timestamp
            )
        """)
        con.execute("""
            create table electricity (
                bill decimal,
                bill_date date primary key,
                charge decimal,
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
            create table tithing_income (
                amount decimal,
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
                entry_date date,
                weight decimal
            )
        """)
        schema_versions_insert(con, 1)


def movie_people_insert(con: sqlite3.Connection, id_: uuid.UUID, person: str) -> None:
    sql = """
        insert into movie_people (id, person) values (:id, :person)
    """
    params = {"id": id_, "person": person}
    con.execute(sql, params)
    con.commit()


def movie_picks_insert(
    con: sqlite3.Connection,
    id_: uuid.UUID,
    person_id: uuid.UUID,
    pick_date: datetime.date,
    pick_text: str,
    pick_url: str,
) -> None:
    sql = """
        insert into movie_picks (
            id, person_id, pick_date, pick_text, pick_url
        ) values (
            :id, :person_id, :pick_date, :pick_text, :pick_url
        )
    """
    params = {
        "id": id_,
        "person_id": person_id,
        "pick_date": pick_date,
        "pick_text": pick_text,
        "pick_url": pick_url,
    }
    con.execute(sql, params)
    con.commit()


def phone_usage_insert(
    con: sqlite3.Connection,
    end_date: datetime.date,
    id_: uuid.UUID,
    megabytes: int,
    messages: int,
    minutes: int,
    start_date: datetime.date,
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
        "id": id_,
        "megabytes": megabytes,
        "messages": messages,
        "minutes": minutes,
        "start_date": start_date,
    }
    con.execute(sql, params)
    con.commit()


def reset_data(con: sqlite3.Connection) -> None:
    sql = [
        "delete from balances_accounts",
        "delete from balances_transactions",
        "delete from billboard_number_one",
        "delete from callings",
        "delete from electricity",
        "delete from hymn_history",
        "delete from hymn_tags",
        "delete from hymns",
        "delete from jar_entries",
        "delete from library_books",
        "delete from library_credentials",
        "delete from movie_people",
        "delete from movie_picks",
        "delete from phone_usage",
        "delete from settings",
        "delete from tithing_income",
        "delete from user_permissions",
        "delete from weight_entries",
    ]
    for s in sql:
        con.execute(s)
    con.commit()


def schema_versions_insert(con: sqlite3.Connection, schema_version: int) -> None:
    sql = """
        insert into schema_versions (schema_version, migration_timestamp)
        values (:schema_version, :migration_timestamp)
    """
    params = {
        "schema_version": schema_version,
        "migration_timestamp": datetime.datetime.now(datetime.UTC),
    }
    con.execute(sql, params)
    con.commit()


def settings_insert(
    con: sqlite3.Connection, setting_id: str, setting_value: str
) -> None:
    sql = """
        insert into settings (
            setting_id, setting_value
        ) values (
            :setting_id, :setting_value
        )
    """
    params = {"setting_id": setting_id, "setting_value": setting_value}
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


def tithing_income_insert(
    con: sqlite3.Connection,
    amount: decimal.Decimal,
    date: datetime.date,
    description: str,
    id_: uuid.UUID,
    tithing_paid: datetime.date,
) -> None:
    sql = """
        insert into tithing_income (
            amount, date, description, id, tithing_paid
        ) values (
            :amount, :date, :description, :id, :tithing_paid
        )
    """
    params = {
        "amount": amount,
        "date": date,
        "description": description,
        "id": id_,
        "tithing_paid": tithing_paid,
    }
    con.execute(sql, params)
    con.commit()


def user_permissions_insert(
    con: sqlite3.Connection, email: str, permissions: str
) -> None:
    sql = """
        insert into user_permissions (email, permissions) values (:email, :permissions)
    """
    params = {"email": email, "permissions": permissions}
    con.execute(sql, params)
    con.commit()


def weight_entries_insert(
    con: sqlite3.Connection, entry_date: datetime.date, weight: decimal.Decimal
) -> None:
    sql = """
        insert into weight_entries (
            entry_date, weight
        ) values (
            :entry_date, :weight
        )
    """
    params = {"entry_date": entry_date, "weight": weight}
    con.execute(sql, params)
    con.commit()
