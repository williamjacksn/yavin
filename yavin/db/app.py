import datetime
import decimal
import uuid

import fort


class YavinDatabase(fort.PostgresDatabase):
    _version: int = None

    # balances

    def balances_accounts_count(self) -> int:
        sql = """
            select count(*)
            from balances_accounts
        """
        return int(self.q_val(sql))

    def balances_accounts_list(self):
        sql = """
            select
                a.id as account_id,
                a.account_name,
                sum(coalesce(t.tx_value, 0)) as account_balance
            from balances_accounts a
            left join balances_transactions t on t.account_id = a.id
            group by a.id, a.account_name
            order by a.account_name
        """
        return self.q(sql)

    def balances_transactions_add(self, params: dict):
        sql = """
            insert into balances_transactions (
                account_id, tx_date, tx_description, tx_value
            ) values (
                %(account_id)s, %(tx_date)s, %(tx_description)s, %(tx_value)s
            )
        """
        self.u(sql, params)

    def balances_transactions_list(self, account_id: uuid.UUID):
        sql = """
            select
                a.id as account_id,
                a.account_name,
                tx_id,
                tx_date,
                tx_description,
                tx_value,
                sum(coalesce(tx_value, 0)) over () account_balance
            from balances_accounts a
            left join balances_transactions t on t.account_id = a.id
            where a.id = %(account_id)s
            order by tx_date desc, tx_description
        """
        params = {
            "account_id": account_id,
        }
        return self.q(sql, params)

    # billboard

    def billboard_get_latest(self):
        sql = """
            select artist, fetched_at, id, title
            from billboard_number_one
            order by fetched_at desc
            limit 1
        """
        return self.q_one(sql)

    def billboard_insert(self, artist: str, title: str):
        sql = """
            insert into billboard_number_one (
                artist, fetched_at, id, title
            ) values (
                %(artist)s, current_timestamp, %(id)s, %(title)s
            )
        """
        params = {
            "artist": artist,
            "id": uuid.uuid4(),
            "title": title,
        }
        self.u(sql, params)

    def billboard_update_fetched_at(self, _id):
        sql = """
            update billboard_number_one
            set fetched_at = current_timestamp
            where id = %(id)s
        """
        params = {
            "id": _id,
        }
        self.u(sql, params)

    # captain's log

    def captains_log_delete(self, id_: str):
        sql = """
            delete from captains_log
            where id = %(id)s
        """
        params = {"id": uuid.UUID(hex=id_)}
        self.u(sql, params)

    def captains_log_get(self, log_id: uuid.UUID) -> dict | None:
        sql = """
            select id, log_text, log_timestamp from captains_log
            where id = %(id)s
        """
        params = {"id": log_id}
        row = self.q_one(sql, params)
        if row:
            return {
                "id": row.get("id"),
                "log_text": row.get("log_text"),
                "log_timestamp": row.get("log_timestamp"),
            }

    def captains_log_insert(
        self, log_text: str, log_timestamp: datetime.datetime = None
    ):
        sql = """
            insert into captains_log (id, log_timestamp, log_text)
            values (%(id)s, %(log_timestamp)s, %(log_text)s)
        """
        if log_timestamp is None:
            log_timestamp = datetime.datetime.utcnow()
        params = {
            "id": uuid.uuid4(),
            "log_text": log_text,
            "log_timestamp": log_timestamp,
        }
        self.u(sql, params)

    def captains_log_list(self, limit: int = 20) -> list[dict]:
        sql = """
            select id, log_timestamp, log_text
            from captains_log
            order by log_timestamp desc
            limit %(limit)s
        """
        params = {"limit": limit}
        return self.q(sql, params)

    def captains_log_update(self, id_: str, log_text: str):
        sql = """
            update captains_log
            set log_text = %(log_text)s
            where id = %(id)s
        """
        params = {"id": uuid.UUID(hex=id_), "log_text": log_text}
        self.u(sql, params)

    # electricity

    def electricity_insert(
        self,
        bill_date: datetime.date,
        kwh: int,
        charge: decimal.Decimal,
        bill: decimal.Decimal,
    ):
        sql = """
            insert into electricity (bill_date, kwh, charge, bill)
            values (%(bill_date)s, %(kwh)s, %(charge)s, %(bill)s)
        """
        params = {"bill_date": bill_date, "kwh": kwh, "charge": charge, "bill": bill}
        self.u(sql, params)

    def electricity_list(self):
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
        return self.q(sql)

    # gas prices

    def gas_prices_delete(self, id_: str):
        sql = """
            delete from gas_prices
            where id = %(id)s
        """
        params = {"id": id_}
        self.u(sql, params)

    def gas_prices_insert(
        self,
        price_date: datetime.date,
        price: decimal.Decimal,
        gallons: decimal.Decimal = None,
        location: str = None,
        vehicle: str = None,
        miles_driven: decimal.Decimal = None,
    ):
        sql = """
            insert into gas_prices (
                id, price_date, price, gallons, location,
                vehicle, miles_driven
            ) values (
                %(id)s, %(price_date)s, %(price)s, %(gallons)s, %(location)s,
                %(vehicle)s, %(miles_driven)s
            )
        """
        params = {
            "id": uuid.uuid4(),
            "price_date": price_date,
            "price": price,
            "gallons": gallons,
            "location": location,
            "vehicle": vehicle,
            "miles_driven": miles_driven,
        }
        self.u(sql, params)

    def gas_prices_list(self, limit: int = 20) -> list[dict]:
        sql = """
            select id, price_date, price, gallons, location, vehicle, miles_driven
            from gas_prices
            order by price_date desc
            limit %(limit)s
        """
        params = {"limit": limit}
        return self.q(sql, params)

    # jar

    def jar_entries_days_since_last(self) -> int:
        """Get the number of days since the last jar entry. If the last jar entry was
        today (or in the future), return 0. If there is no jar entry, return -1"""
        sql = """
            select max(entry_date) last_entry
            from jar_entries
        """
        last_entry = self.q_val(sql)
        if last_entry is None:
            return -1
        if last_entry > datetime.date.today():
            return 0
        return (datetime.date.today() - last_entry).days

    def jar_entries_insert(self, entry_date: datetime.date):
        sql = """
            select max(id) max_id
            from jar_entries
        """
        last: int = self.q_val(sql)
        if last is None:
            last = 0
        sql = """
            insert into jar_entries (id, entry_date)
            values (%(id)s, %(entry_date)s)
        """
        params = {"id": last + 1, "entry_date": entry_date}
        self.u(sql, params)

    def jar_entries_list(self, page: int = 1) -> list[dict]:
        sql = """
            select id, entry_date
            from jar_entries
            order by entry_date desc, id
            limit 11 offset %(offset)s
        """
        params = {
            "offset": 10 * (page - 1),
        }
        return self.q(sql, params)

    # library

    def library_credentials_delete(self, params: dict):
        sql = """
            delete from library_credentials
            where id = %(id)s
        """
        self.u(sql, params)

    def library_credentials_get(self, params: dict):
        sql = """
            select c.library, c.username, c.password, c.library_type
            from library_books b
            join library_credentials c on c.id = b.credential_id
            where item_id = %(item_id)s
        """
        return self.q_one(sql, params)

    def library_credentials_insert(self, params: dict):
        sql = """
            insert into library_credentials (
                id, library, username, password, display_name,
                library_type
            ) values (
                %(id)s, %(library)s, %(username)s, %(password)s, %(display_name)s,
                %(library_type)s
            )
        """
        params.update({"id": uuid.uuid4()})
        self.u(sql, params)

    def library_credentials_list(self) -> list[dict]:
        sql = """
            select id, library, username, password, display_name, balance, library_type
            from library_credentials
            order by display_name
        """
        return self.q(sql)

    def library_credentials_update(self, params: dict):
        sql = """
            update library_credentials
            set balance = %(balance)s
            where id = %(id)s
        """
        self.u(sql, params)

    def library_books_count(self):
        sql = """
            select
                count(*) books_count,
                count(*) filter (where due < current_date) overdue_count
            from library_books
        """
        return self.q_one(sql)

    def library_books_insert(self, params: dict):
        sql = """
            insert into library_books (
                id, credential_id, title, due, renewable,
                item_id, medium
            ) values (
                %(id)s, %(credential_id)s, %(title)s, %(due)s, %(renewable)s,
                %(item_id)s, %(medium)s
            )
        """
        params.update({"id": uuid.uuid4()})
        self.u(sql, params)

    def library_books_list(self):
        sql = """
            select c.display_name, b.title, b.due, b.renewable, b.item_id, b.medium
            from library_books b
            join library_credentials c on c.id = b.credential_id
            order by due, title
        """
        return self.q(sql)

    def library_books_list_due(self):
        sql = """
            select b.title, b.due, b.medium, c.display_name account_name
            from library_books b
            join library_credentials c on c.id = b.credential_id
            where b.due <= current_date
            order by c.display_name, b.title
        """
        return self.q(sql)

    def library_books_truncate(self):
        sql = """
            truncate table library_books
        """
        self.u(sql)

    def library_books_update(self, params: dict):
        sql = """
            update library_books
            set due = %(due)s
            where item_id = %(item_id)s
        """
        return self.u(sql, params)

    # movie night

    def movie_people_insert(self, params: dict):
        sql = """
            insert into movie_people (id, person)
            values (%(id)s, %(person)s)
        """
        params.update({"id": uuid.uuid4()})
        self.u(sql, params)

    def movie_people_list(self):
        sql = """
            select
                movie_people.id,
                person,
                row_number() over (order by max(pick_date) nulls first) pick_order
            from movie_people
            left join movie_picks on movie_people.id = movie_picks.person_id
            group by person, movie_people.id
            order by person, pick_order
        """
        return self.q(sql)

    def movie_people_next_pick(self):
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
        return self.q_one(sql)

    def movie_picks_delete(self, params: dict):
        sql = """
            delete from movie_picks
            where id = %(id)s
        """
        self.u(sql, params)

    def movie_picks_get(self, pick_id: uuid.UUID) -> dict | None:
        sql = """
            select id, person_id, pick_date, pick_text, pick_url
            from movie_picks
            where id = %(id)s
        """
        params = {"id": pick_id}
        return self.q_one(sql, params)

    def movie_picks_insert(self, params: dict):
        sql = """
            insert into movie_picks (id, pick_date, person_id, pick_text, pick_url)
            values (%(id)s, %(pick_date)s, %(person_id)s, %(pick_text)s, %(pick_url)s)
        """
        params.update({"id": uuid.uuid4()})
        if params.get("pick_url") == "":
            params.update({"pick_url": None})
        self.u(sql, params)

    def movie_picks_list(self):
        sql = """
            select movie_picks.id, pick_date, person_id, person, pick_text, pick_url
            from movie_picks
            join movie_people on movie_picks.person_id = movie_people.id
            order by pick_date desc, movie_picks.id
        """
        return self.q(sql)

    def movie_picks_update(self, params: dict):
        sql = """
            update movie_picks
            set pick_date = %(pick_date)s, person_id = %(person_id)s,
                pick_text = %(pick_text)s, pick_url = %(pick_url)s
            where id = %(id)s
        """
        if params.get("pick_url") == "":
            params.update({"pick_url": None})
        self.u(sql, params)

    # phone usage

    def phone_usage_insert(
        self,
        start_date: datetime.date,
        end_date: datetime.date,
        minutes: int,
        messages: int,
        megabytes: int,
    ):
        sql = """
            insert into phone_usage (
                id, start_date, end_date, minutes, messages,
                megabytes
            ) values (
                %(id)s, %(start_date)s, %(end_date)s, %(minutes)s, %(messages)s,
                %(megabytes)s
            )
        """
        params = {
            "id": uuid.uuid4(),
            "start_date": start_date,
            "end_date": end_date,
            "minutes": minutes,
            "messages": messages,
            "megabytes": megabytes,
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

    def settings_delete(self, setting_id: str):
        sql = """
            delete from settings where setting_id = %(setting_id)s
        """
        params = {"setting_id": setting_id}
        self.u(sql, params)

    def settings_list(self) -> dict[str, str]:
        sql = """
            select setting_id, setting_value
            from settings
        """
        return {s.get("setting_id"): s.get("setting_value") for s in self.q(sql)}

    def settings_update(self, setting_id: str, setting_value: str):
        sql = """
            insert into settings (setting_id, setting_value)
            values (%(setting_id)s, %(setting_value)s)
            on conflict (setting_id) do update set setting_value = %(setting_value)s
        """
        params = {"setting_id": setting_id, "setting_value": setting_value}
        self.u(sql, params)

    # tithing

    def tithing_get_current_owed(self) -> decimal.Decimal:
        sql = """
            select round(coalesce(sum(amount), 0) * 0.1, 2) tithing_owed
            from tithing_income
            where tithing_paid is null
        """
        return self.q_val(sql)

    def tithing_income_insert(
        self, date: datetime.date, amount: decimal.Decimal, description: str
    ):
        sql = """
            insert into tithing_income (date, amount, description)
            values (%(date)s, %(amount)s, %(description)s)
        """
        params = {
            "date": date,
            "amount": amount,
            "description": description,
        }
        self.u(sql, params)

    def tithing_income_list_unpaid(self):
        sql = """
            select id, date, amount, description
            from tithing_income
            where tithing_paid is null
            order by date, description, id
        """
        return self.q(sql)

    def tithing_income_mark_paid(self):
        sql = """
            update tithing_income
            set tithing_paid = current_date
            where tithing_paid is null
        """
        self.u(sql)

    # user permissions

    def user_permissions_add(self, email: str, permission: str):
        existing_permissions = self.user_permissions_get(email)
        if permission in existing_permissions:
            self.log.debug(f"{email} already has permission {permission}")
            return
        new_permissions = existing_permissions + [permission]
        self.user_permissions_set(email, new_permissions)

    def user_permissions_get(self, email: str) -> list[str]:
        sql = """
            select permissions from user_permissions where email = %(email)s
        """
        params = {
            "email": email,
        }
        permissions = self.q_val(sql, params)
        if permissions:
            return sorted(set(permissions.split()))
        return []

    def user_permissions_list(self) -> list[dict]:
        sql = """
            select email, permissions
            from user_permissions
            order by email
        """
        result = []
        for row in self.q(sql):
            result.append(
                {
                    "email": row.get("email"),
                    "permissions": sorted(set(row.get("permissions").split())),
                }
            )
        return result

    def user_permissions_set(self, email: str, permissions: list[str]):
        sql = """
            insert into user_permissions (
                email, permissions
            ) values (
                %(email)s, %(permissions)s
            ) on conflict (email) do update set
                permissions = %(permissions)s
        """
        params = {"email": email, "permissions": " ".join(sorted(set(permissions)))}
        self.u(sql, params)

    # weight

    def weight_entries_get_for_date(
        self, entry_date: datetime.date
    ) -> decimal.Decimal | None:
        sql = """
            select entry_date, weight
            from weight_entries
            where entry_date = %(entry_date)s
        """
        params = {"entry_date": entry_date}
        return self.q_val(sql, params)

    def weight_entries_get_most_recent(self) -> dict | None:
        sql = """
            select entry_date, weight
            from weight_entries
            order by entry_date desc
            limit 1
        """
        return self.q_one(sql)

    def weight_entries_insert(self, entry_date: datetime.date, weight: decimal.Decimal):
        sql = """
            insert into weight_entries (entry_date, weight)
            values (%(entry_date)s, %(weight)s)
            on conflict (entry_date) do nothing
        """
        params = {"entry_date": entry_date, "weight": weight}
        self.u(sql, params)

    def weight_entries_list(self, limit: int = 10) -> list[dict]:
        sql = """
            select entry_date, weight
            from weight_entries
            order by entry_date desc
            limit %(limit)s
        """
        params = {"limit": limit}
        return self.q(sql, params)

    # migrations and metadata

    def migrate(self):
        self.log.debug(f"The database is at schema version {self.version}")
        self.log.debug("Checking for database migrations ...")
        if self.version < 17:
            self.log.debug("Migrating to version 17")
            self.u("""
                create extension if not exists pgcrypto
            """)
            self.u("""
                create table captains_log (
                    id uuid primary key,
                    log_timestamp timestamp not null,
                    log_text text not null
                )
            """)
            self.u("""
                create table electricity (
                    bill_date date primary key,
                    kwh integer not null,
                    charge numeric(10, 2) not null,
                    bill numeric(10, 2) not null
                )
            """)
            self.u("""
                create table flags (
                    flag_name text primary key,
                    flag_value text not null
                )
            """)
            self.u("""
                create table gas_prices (
                    id uuid primary key,
                    price_date date not null,
                    price numeric not null,
                    gallons numeric,
                    location text,
                    vehicle text,
                    miles_driven numeric
                )
            """)
            self.u("""
                create table hymns (
                    hymn_number integer primary key,
                    title text not null,
                    first_line text
                )
            """)
            self.u("""
                create table hymn_tags (
                    hymn_number integer not null references hymns,
                    tag text not null,
                    primary key (hymn_number, tag)
                )
            """)
            self.u("""
                create table hymn_history (
                    hymn_number integer references hymns,
                    date date not null
                )
            """)
            self.u("""
                create table jar_entries (
                    id integer primary key,
                    entry_date date not null,
                    paid boolean default false not null
                )
            """)
            self.u("""
                create table library_credentials (
                    id uuid primary key,
                    library text not null,
                    username text not null,
                    password text not null,
                    display_name text not null,
                    balance integer not null default 0
                )
            """)
            self.u("""
                create table library_books (
                    id uuid primary key,
                    credential_id uuid
                        references library_credentials (id)
                        on delete cascade,
                    title text not null,
                    due date not null,
                    renewable boolean not null,
                    item_id text not null default '',
                    medium text not null default ''
                )
            """)
            self.u("""
                create table movie_people (
                    id uuid primary key,
                    person text not null
                )
            """)
            self.u("""
                create table movie_picks (
                    id uuid primary key,
                    pick_date date not null,
                    person_id uuid references movie_people (id) on delete set null,
                    pick_text text not null,
                    pick_url text
                )
            """)
            self.u("""
                create table packages (
                    tracking_number text primary key,
                    shipper text,
                    notes text,
                    expected_at date,
                    arrived_at date
                )
            """)
            self.u("""
                create table phone_usage (
                    id uuid primary key default gen_random_uuid(),
                    start_date date not null,
                    end_date date not null,
                    minutes int not null,
                    messages int not null,
                    megabytes int not null
                )
            """)
            self.u("""
                create table schema_versions (
                    schema_version integer primary key,
                    migration_date timestamp not null
                )
            """)
            self.u("""
                create table timeline_entries (
                    id uuid primary key,
                    start_date date not null,
                    end_date date not null,
                    description text not null,
                    zoom_level integer not null default 1,
                    tags text
                )
            """)
            self.u("""
                create table weight_entries (
                    entry_date date primary key,
                    weight numeric not null check (weight > 0)
                )
            """)
            self._add_schema_version(17)
        if self.version < 18:
            self.log.debug("Migrating to version 18")
            self.u("""
                create table settings (
                    setting_id text primary key,
                    setting_value text
                )
            """)
            self._add_schema_version(18)
        if self.version < 19:
            self.log.debug("Migrating to version 19")
            self.u("""
                create table user_permissions (
                    email text primary key,
                    permissions text
                )
            """)
            self.u("""
                create table balances_accounts (
                    id uuid primary key default gen_random_uuid(),
                    account_name text not null
                )
            """)
            self.u("""
                create table balances_transactions (
                    tx_id uuid primary key default gen_random_uuid(),
                    account_id uuid not null
                        references balances_accounts(id)
                        on delete cascade,
                    tx_date date not null,
                    tx_description text,
                    tx_value numeric not null
                )
            """)
            self._add_schema_version(19)
        if self.version < 20:
            self.log.debug("Migrating to version 20")
            self.u("""
                alter table library_credentials
                add library_type text not null default 'biblionix'
            """)
            self._add_schema_version(20)
        if self.version < 21:
            self.log.debug("Migrating to version 21")
            self.u("""
                create table tithing_income (
                    id uuid primary key default gen_random_uuid(),
                    date date not null,
                    amount numeric not null,
                    description text,
                    tithing_paid date
                )
            """)
            self._add_schema_version(21)
        if self.version < 22:
            self.log.debug("Migrating to version 22")
            self.u("""
                create table billboard_number_one (
                    id uuid primary key,
                    fetched_at timestamptz not null,
                    artist text not null,
                    title text not null
                )
            """)
            self._add_schema_version(22)
        if self.version < 23:
            self.log.debug("Migrating to version 23")
            self.u("""
                create table callings (
                   id uuid primary key default gen_random_uuid(),
                   ward text not null,
                   calling text not null,
                   sustained_at date not null,
                   set_apart_at date,
                   released_at date
                )
            """)
            self._add_schema_version(23)

    def _add_schema_version(self, schema_version: int):
        self._version = schema_version
        sql = """
            insert into schema_versions (schema_version, migration_date)
            values (%(schema_version)s, %(migration_date)s)
        """
        params = {
            "schema_version": schema_version,
            "migration_date": datetime.datetime.utcnow(),
        }
        self.u(sql, params)

    def _table_exists(self, table_name: str) -> bool:
        sql = """
            select count(*) table_count
            from information_schema.tables
            where table_name = %(table_name)s
        """
        params = {"table_name": table_name}
        for record in self.q(sql, params):
            if record["table_count"] == 0:
                return False
        return True

    @property
    def version(self) -> int:
        if self._version is None:
            self._version = 0
            if self._table_exists("schema_versions"):
                sql = """
                    select max(schema_version) current_version
                    from schema_versions
                """
                current_version = self.q_val(sql)
                if current_version is not None:
                    self._version = current_version
        return self._version
