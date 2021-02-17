import datetime
import decimal
import fort
import psycopg2
import uuid

from typing import Dict, List


class YavinDatabase(fort.PostgresDatabase):

    # captain's log

    def add_captains_log_entry(self, log_text: str, log_timestamp: datetime.datetime = None):
        sql = 'insert into captains_log (id, log_timestamp, log_text) values (%(id)s, %(log_timestamp)s, %(log_text)s)'
        if log_timestamp is None:
            log_timestamp = datetime.datetime.utcnow()
        params = {'id': uuid.uuid4(), 'log_text': log_text, 'log_timestamp': log_timestamp}
        self.u(sql, params)

    def delete_captains_log_entry(self, id_: str):
        sql = 'delete from captains_log where id = %(id)s'
        params = {'id': uuid.UUID(hex=id_)}
        self.u(sql, params)

    def get_captains_log_entries(self, limit: int = 20) -> List[Dict]:
        sql = 'select id, log_timestamp, log_text from captains_log order by log_timestamp desc limit %(limit)s'
        params = {'limit': limit}
        return self.q(sql, params)

    def update_captains_log_entry(self, id_: str, log_text: str):
        sql = 'update captains_log set log_text = %(log_text)s where id = %(id)s'
        params = {'id': uuid.UUID(hex=id_), 'log_text': log_text}
        self.u(sql, params)

    # gas prices

    def add_gas_price_entry(self, price_date: datetime.date, price: decimal.Decimal, gallons: decimal.Decimal = None,
                            location: str = None, vehicle: str = None, miles_driven: decimal.Decimal = None):
        sql = '''
            insert into gas_prices (id, price_date, price, gallons, location, vehicle, miles_driven)
            values (%(id)s, %(price_date)s, %(price)s, %(gallons)s, %(location)s, %(vehicle)s, %(miles_driven)s)
        '''
        params = {'id': uuid.uuid4(), 'price_date': price_date, 'price': price, 'gallons': gallons,
                  'location': location, 'vehicle': vehicle, 'miles_driven': miles_driven}
        self.u(sql, params)

    def delete_gas_price_entry(self, id_: str):
        sql = 'delete from gas_prices where id = %(id)s'
        params = {'id': id_}
        self.u(sql, params)

    def get_gas_price_entries(self, limit: int = 20) -> List[Dict]:
        sql = '''
            select id, price_date, price, gallons, location, vehicle, miles_driven
            from gas_prices
            order by price_date desc
            limit %(limit)s
        '''
        params = {'limit': limit}
        return self.q(sql, params)

    # jar

    def add_jar_entry(self, entry_date: datetime.date):
        last: int = self.q_val('select max(id) max_id from jar_entries')
        if last is None:
            last = 0
        params = {
            'id': last + 1,
            'entry_date': entry_date
        }
        self.u('insert into jar_entries (id, entry_date) values (%(id)s, %(entry_date)s)', params)

    def get_recent_jar_entries(self, limit: int = 10) -> List[Dict]:
        params = {'limit': limit}
        return self.q('select id, entry_date from jar_entries order by entry_date desc limit %(limit)s', params)

    # library

    def add_library_credential(self, params: Dict):
        params['id'] = uuid.uuid4()
        self.u('''
            insert into library_credentials (id, library, username, password, display_name)
            values (%(id)s, %(library)s, %(username)s, %(password)s, %(display_name)s)
        ''', params)

    def get_library_credentials(self) -> List[Dict]:
        return self.q('select id, library, username, password, display_name, balance from library_credentials')

    def delete_library_credential(self, params: Dict):
        self.u('delete from library_credentials where id = %(id)s', params)

    def update_balance(self, params: Dict):
        self.u('update library_credentials set balance = %(balance)s where id = %(id)s', params)

    def add_library_book(self, params: Dict):
        params['id'] = uuid.uuid4()
        sql = '''
            insert into library_books (id, credential_id, title, due, renewable, item_id, medium)
            values (%(id)s, %(credential_id)s, %(title)s, %(due)s, %(renewable)s, %(item_id)s, %(medium)s)
        '''
        self.u(sql, params)

    def update_due_date(self, params: Dict):
        sql = 'update library_books set due = %(due)s where item_id = %(item_id)s'
        return self.u(sql, params)

    def clear_library_books(self):
        self.u('truncate table library_books')

    def get_book_credentials(self, params: Dict):
        sql = '''
            select library, username, password
            from library_books
            join library_credentials on library_credentials.id = library_books.credential_id
            where item_id = %(item_id)s
        '''
        return self.q_one(sql, params)

    def get_library_books(self):
        sql = '''
            select display_name, title, due, renewable, item_id, medium
            from library_books
            join library_credentials on library_credentials.id = library_books.credential_id
        '''
        return self.q(sql)

    # weight

    def add_weight_entry(self, entry_date: datetime.date, weight: float):
        params = {'entry_date': entry_date, 'weight': weight}
        try:
            self.u('insert into weight_entries (entry_date, weight) values (%(entry_date)s, %(weight)s)', params)
        except psycopg2.IntegrityError:
            return f'There is already a weight entry for {entry_date}.'

    def get_recent_weight_entries(self, limit: int = 10) -> List[Dict]:
        params = {'limit': limit}
        return self.q('select entry_date, weight from weight_entries order by entry_date desc limit %(limit)s', params)

    def get_weight_most_recent(self) -> float:
        row = self.q_one('select weight from weight_entries order by entry_date desc')
        if row is None:
            return 0
        return row['weight']

    # movie night

    def add_movie_night_person(self, params: Dict):
        params['id'] = uuid.uuid4()
        sql = 'insert into movie_people (id, person) values (%(id)s, %(person)s)'
        self.u(sql, params)

    def get_movie_night_people(self):
        sql = '''
            select movie_people.id, person, row_number() over (order by max(pick_date) nulls first) pick_order
            from movie_people
            left join movie_picks on movie_people.id = movie_picks.person_id
            group by person, movie_people.id
        '''
        return self.q(sql)

    def add_movie_night_pick(self, params: Dict):
        params['id'] = uuid.uuid4()
        if params['pick_url'] == '':
            params['pick_url'] = None
        sql = '''
            insert into movie_picks (id, pick_date, person_id, pick_text, pick_url)
            values (%(id)s, %(pick_date)s, %(person_id)s, %(pick_text)s, %(pick_url)s)
        '''
        self.u(sql, params)

    def delete_movie_night_pick(self, params: Dict):
        sql = 'delete from movie_picks where id = %(id)s'
        self.u(sql, params)

    def edit_movie_night_pick(self, params: Dict):
        if params['pick_url'] == '':
            params['pick_url'] = None
        sql = '''
            update movie_picks
            set pick_date = %(pick_date)s, person_id = %(person_id)s, pick_text = %(pick_text)s, pick_url = %(pick_url)s
            where id = %(id)s
        '''
        self.u(sql, params)

    def get_movie_night_picks(self):
        sql = '''
            select movie_picks.id, pick_date, person_id, person, pick_text, pick_url
            from movie_picks
            join movie_people on movie_picks.person_id = movie_people.id
        '''
        return self.q(sql)

    # electricity

    def add_electricity(self, bill_date: datetime.date, kwh: int, charge: decimal.Decimal, bill: decimal.Decimal):
        sql = '''
            insert into electricity (bill_date, kwh, charge, bill)
            values (%(bill_date)s, %(kwh)s, %(charge)s, %(bill)s)
        '''
        params = {'bill_date': bill_date, 'kwh': kwh, 'charge': charge, 'bill': bill}
        self.u(sql, params)

    def get_electricity(self):
        sql = 'select bill_date, kwh, charge, bill from electricity order by bill_date desc'
        return self.q(sql)

    # phone usage

    def add_phone_usage(self, start_date: datetime.date, end_date: datetime.date,
                        minutes: int, messages: int, megabytes: int):
        sql = '''
            insert into phone_usage (id, start_date, end_date, minutes, messages, megabytes)
            values (%(id)s, %(start_date)s, %(end_date)s, %(minutes)s, %(messages)s, %(megabytes)s)
        '''
        params = {
            'id': uuid.uuid4(),
            'start_date': start_date,
            'end_date': end_date,
            'minutes': minutes,
            'messages': messages,
            'megabytes': megabytes
        }
        self.u(sql, params)

    def get_phone_usage(self) -> list[dict]:
        sql = '''
            select id, start_date, end_date, minutes, messages, megabytes
            from phone_usage
            order by end_date desc
        '''
        return self.q(sql)

    # migrations and metadata

    def migrate(self):
        self.log.debug(f'The database is at schema version {self.version}')
        self.log.debug('Checking for database migrations ...')
        if self.version == 0:
            self.log.debug('Migrating from version 0 to version 1')
            self.u('''
                create table flags (
                    flag_name text primary key,
                    flag_value text not null
                )
            ''')
            self._insert_flag('db_version', '1')
        if self.version == 1:
            self.log.debug('Migrating from version 1 to version 2')
            self.u('''
                create table jar_entries (
                    id integer primary key,
                    entry_date date not null,
                    paid boolean default false not null
                )
            ''')
            self.u('''
                create table weight_entries (
                    entry_date date primary key,
                    weight numeric not null check (weight > 0)
                )
            ''')
            self._update_flag('db_version', '2')
        if self.version == 2:
            self.log.debug('Migrating from version 2 to version 3')
            self.u('''
                create table library_credentials (
                    id uuid primary key,
                    library text not null,
                    username text not null,
                    password text not null,
                    display_name text not null
                )
            ''')
            self._update_flag('db_version', '3')
        if self.version == 3:
            self.log.debug('Migrating from version 3 to version 4')
            self.u('''
                create table library_books (
                    id uuid primary key,
                    credential_id uuid references library_credentials (id) on delete cascade,
                    title text not null,
                    due date not null,
                    renewable boolean not null
                )
            ''')
            self._update_flag('db_version', '4')
        if self.version == 4:
            self.log.debug('Migrating from version 4 to version 5')
            self.u("alter table library_books add column item_id text not null default ''")
            self._update_flag('db_version', '5')
        if self.version == 5:
            self.log.debug('Migrating from version 5 to version 6')
            self.u("alter table library_books add column medium text not null default ''")
            self._update_flag('db_version', '6')
        if self.version == 6:
            self.log.debug('Migrating from version 6 to version 7')
            self.u('''
                create table movie_people (
                    id uuid primary key,
                    person text not null
                )
            ''')
            self.u('''
                create table movie_picks (
                    id uuid primary key,
                    pick_date date not null,
                    person_id uuid references movie_people (id) on delete set null,
                    pick_text text not null
                )
            ''')
            self._update_flag('db_version', '7')
        if self.version == 7:
            self.log.debug('Migrating from version 7 to version 8')
            self.u('''
                create table electricity (
                    bill_date date primary key,
                    kwh integer not null,
                    charge integer not null,
                    bill integer not null
                )
            ''')
            self._update_flag('db_version', '8')
        if self.version == 8:
            self.log.debug('Migrating from version 8 to version 9')
            self.u('''
                create table timeline_entries (
                    id uuid primary key,
                    start_date date not null,
                    end_date date not null,
                    description text not null,
                    zoom_level integer not null default 1,
                    tags text
                )
            ''')
            self._update_flag('db_version', '9')
        if self.version == 9:
            self.log.debug('Migrating from version 9 to version 10')
            self.u('''
                alter table library_credentials
                add column balance integer not null default 0
            ''')
            self._update_flag('db_version', '10')
        if self.version == 10:
            self.log.debug('Migrating from version 10 to version 11')
            self.u('''
                create table schema_versions (
                    schema_version integer primary key,
                    migration_date timestamp not null
                )
            ''')
            self.u('''
                create table captains_log (
                    id uuid primary key,
                    log_timestamp timestamp not null,
                    log_text text not null
                )
            ''')
            self._delete_flag('db_version')
            self._add_schema_version(11)
        if self.version == 11:
            self.log.debug('Migrating from version 11 to version 12')
            self.u('''
                create table gas_prices (
                    id uuid primary key,
                    price_date date not null,
                    price numeric not null,
                    gallons numeric,
                    location text,
                    vehicle text,
                    miles_driven numeric
                )
            ''')
            self._add_schema_version(12)
        if self.version == 12:
            self.log.debug('Migrating from version 12 to version 13')
            self.u('''
                alter table movie_picks
                add column pick_url text
            ''')
            self._add_schema_version(13)
        if self.version == 13:
            self.log.debug('Migrating from version 13 to version 14')
            self.u('''
                alter table electricity
                alter column charge type numeric(10, 2) using (charge / 100.0),
                alter column bill type numeric(10, 2) using (bill / 100.0)
            ''')
            self._add_schema_version(14)
        if self.version < 15:
            self.log.debug('Migrating from version 14 to version 15')
            self.u('''
                create table phone_usage (
                    id uuid primary key,
                    start_date date not null,
                    end_date date not null,
                    minutes int not null,
                    messages int not null,
                    megabytes int not null
                )
            ''')
            self._add_schema_version(15)

    def _insert_flag(self, flag_name: str, flag_value: str):
        sql = 'insert into flags (flag_name, flag_value) values (%(flag_name)s, %(flag_value)s)'
        params = {'flag_name': flag_name, 'flag_value': flag_value}
        self.u(sql, params)

    def _delete_flag(self, flag_name: str):
        sql = 'delete from flags where flag_name = %(flag_name)s'
        params = {'flag_name': flag_name}
        self.u(sql, params)

    def _update_flag(self, flag_name: str, flag_value: str):
        sql = 'update flags set flag_value = %(flag_value)s where flag_name = %(flag_name)s'
        params = {'flag_name': flag_name, 'flag_value': flag_value}
        self.u(sql, params)

    def _add_schema_version(self, schema_version: int):
        sql = '''
            insert into schema_versions (schema_version, migration_date)
            values (%(schema_version)s, %(migration_date)s)
        '''
        self.u(sql, {'schema_version': schema_version, 'migration_date': datetime.datetime.utcnow()})

    def _table_exists(self, table_name: str) -> bool:
        sql = 'select count(*) table_count from information_schema.tables where table_name = %(table_name)s'
        for record in self.q(sql, {'table_name': table_name}):
            if record['table_count'] == 0:
                return False
        return True

    @property
    def version(self):
        if self._table_exists('schema_versions'):
            sql = 'select max(schema_version) current_version from schema_versions'
            for record in self.q(sql):
                return record['current_version']
        if self._table_exists('flags'):
            sql = 'select flag_value from flags where flag_name = %(flag_name)s'
            for record in self.q(sql, {'flag_name': 'db_version'}):
                return int(record['flag_value'])
        return 0
