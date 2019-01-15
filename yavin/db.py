import datetime
import logging
import psycopg2
import psycopg2.extras
import uuid

from typing import Dict, List, Optional

log = logging.getLogger(__name__)
psycopg2.extras.register_uuid()


class YavinDatabase:
    def __init__(self, dsn: str):
        log.debug('Connecting to database ...')
        try:
            self.cnx = psycopg2.connect(dsn=dsn, cursor_factory=psycopg2.extras.RealDictCursor)
        except psycopg2.OperationalError:
            log.critical('I could not connect to the database!')
            raise
        self.cnx.autocommit = True

    def _q(self, sql: str, args: Dict = None) -> List[Dict]:
        if args is None:
            args = {}
        with self.cnx.cursor() as c:
            c.execute(sql, args)
            return c.fetchall()

    def _q_one(self, sql: str, args: Dict = None) -> Optional[Dict]:
        for row in self._q(sql, args):
            return row
        return None

    def _u(self, sql: str, args: Dict = None) -> int:
        if args is None:
            args = {}
        with self.cnx.cursor() as c:
            c.execute(sql, args)
            return c.rowcount

    # captain's log

    def add_captains_log_entry(self, log_text: str, log_timestamp: datetime.datetime = None):
        sql = 'INSERT INTO captains_log (id, log_timestamp, log_text) VALUES (%(id)s, %(log_timestamp)s, %(log_text)s)'
        if log_timestamp is None:
            log_timestamp = datetime.datetime.utcnow()
        params = {'id': uuid.uuid4(), 'log_text': log_text, 'log_timestamp': log_timestamp}
        self._u(sql, params)

    def delete_captains_log_entry(self, id_: str):
        sql = 'DELETE FROM captains_log WHERE id = %(id)s'
        params = {'id': uuid.UUID(hex=id_)}
        self._u(sql, params)

    def get_captains_log_entries(self, limit: int = 20) -> List[Dict]:
        sql = 'SELECT id, log_timestamp, log_text FROM captains_log ORDER BY log_timestamp DESC LIMIT %(limit)s'
        params = {'limit': limit}
        return self._q(sql, params)

    def update_captains_log_entry(self, id_: str, log_text: str):
        sql = 'UPDATE captains_log SET log_text = %(log_text)s WHERE id = %(id)s'
        params = {'id': uuid.UUID(hex=id_), 'log_text': log_text}
        self._u(sql, params)

    # jar

    def add_jar_entry(self, entry_date: datetime.date):
        last = self._q_one('SELECT max(id) id FROM jar_entries')
        params = {
            'id': last['id'] + 1,
            'entry_date': entry_date
        }
        self._u('INSERT INTO jar_entries (id, entry_date) VALUES (%(id)s, %(entry_date)s)', params)

    def get_recent_jar_entries(self, limit: int = 10) -> List[Dict]:
        params = {'limit': limit}
        return self._q('SELECT id, entry_date FROM jar_entries ORDER BY entry_date DESC LIMIT %(limit)s', params)

    # library

    def add_library_credential(self, params: Dict):
        params['id'] = uuid.uuid4()
        self._u('''
            INSERT INTO library_credentials (id, library, username, password, display_name)
            VALUES (%(id)s, %(library)s, %(username)s, %(password)s, %(display_name)s)
        ''', params)

    def get_library_credentials(self) -> List[Dict]:
        return self._q('SELECT id, library, username, password, display_name, balance FROM library_credentials')

    def delete_library_credential(self, params: Dict):
        self._u('DELETE FROM library_credentials WHERE id = %(id)s', params)

    def update_balance(self, params: Dict):
        self._u('UPDATE library_credentials SET balance = %(balance)s WHERE id = %(id)s', params)

    def add_library_book(self, params: Dict):
        params['id'] = uuid.uuid4()
        sql = '''
            INSERT INTO library_books (id, credential_id, title, due, renewable, item_id, medium)
            VALUES (%(id)s, %(credential_id)s, %(title)s, %(due)s, %(renewable)s, %(item_id)s, %(medium)s)
        '''
        self._u(sql, params)

    def update_due_date(self, params: Dict):
        sql = 'UPDATE library_books SET due = %(due)s WHERE item_id = %(item_id)s'
        return self._u(sql, params)

    def clear_library_books(self):
        self._u('DELETE FROM library_books')

    def get_book_credentials(self, params: Dict):
        sql = '''
            SELECT library, username, password
            FROM library_books
            JOIN library_credentials ON library_credentials.id = library_books.credential_id
            WHERE item_id = %(item_id)s
        '''
        return self._q_one(sql, params)

    def get_library_books(self):
        sql = '''
            SELECT display_name, title, due, renewable, item_id, medium
            FROM library_books
            JOIN library_credentials ON library_credentials.id = library_books.credential_id
        '''
        return self._q(sql)

    # weight

    def add_weight_entry(self, entry_date: datetime.date, weight: float):
        params = {'entry_date': entry_date, 'weight': weight}
        try:
            self._u('INSERT INTO weight_entries (entry_date, weight) VALUES (%(entry_date)s, %(weight)s)', params)
        except psycopg2.IntegrityError:
            return f'There is already a weight entry for {entry_date}.'

    def get_recent_weight_entries(self, limit: int = 10) -> List[Dict]:
        params = {'limit': limit}
        return self._q('SELECT entry_date, weight FROM weight_entries ORDER BY entry_date DESC LIMIT %(limit)s', params)

    def get_weight_most_recent(self) -> float:
        row = self._q_one('SELECT weight FROM weight_entries ORDER BY entry_date DESC')
        if row is None:
            return 0
        return row['weight']

    # movie night

    def add_movie_night_person(self, params: Dict):
        params['id'] = uuid.uuid4()
        sql = 'INSERT INTO movie_people (id, person) VALUES (%(id)s, %(person)s)'
        self._u(sql, params)

    def get_movie_night_people(self):
        sql = '''
            SELECT person_id id, person, row_number() OVER (ORDER BY MAX(pick_date)) pick_order
            FROM movie_picks
            JOIN movie_people ON movie_people.id = movie_picks.person_id
            GROUP BY person, person_id
        '''
        return self._q(sql)

    def add_movie_night_pick(self, params: Dict):
        params['id'] = uuid.uuid4()
        sql = '''
            INSERT INTO movie_picks (id, pick_date, person_id, pick_text)
            VALUES (%(id)s, %(pick_date)s, %(person_id)s, %(pick_text)s)
        '''
        self._u(sql, params)

    def get_movie_night_picks(self):
        sql = '''
            SELECT movie_picks.id, pick_date, person_id, person, pick_text
            FROM movie_picks
            JOIN movie_people ON movie_picks.person_id = movie_people.id
        '''
        return self._q(sql)

    # electricity

    def add_electricity(self, params: Dict):
        sql = '''
            INSERT INTO electricity (bill_date, kwh, charge, bill)
            VALUES (%(bill_date)s, %(kwh)s, %(charge)s, %(bill)s)
        '''
        self._u(sql, params)

    def get_electricity(self):
        sql = 'SELECT bill_date, kwh, charge, bill FROM electricity'
        return self._q(sql)

    def migrate(self):
        log.debug(f'The database is at schema version {self.version}')
        log.debug('Checking for database migrations ...')
        if self.version == 0:
            log.debug('Migrating from version 0 to version 1')
            self._u('''
                CREATE TABLE flags (
                    flag_name TEXT PRIMARY KEY,
                    flag_value TEXT NOT NULL
                )
            ''')
            self._insert_flag('db_version', '1')
        if self.version == 1:
            log.debug('Migrating from version 1 to version 2')
            self._u('''
                CREATE TABLE jar_entries (
                    id INTEGER PRIMARY KEY,
                    entry_date DATE NOT NULL,
                    paid BOOLEAN DEFAULT FALSE NOT NULL
                )
            ''')
            self._u('''
                CREATE TABLE weight_entries (
                    entry_date DATE PRIMARY KEY,
                    weight NUMERIC NOT NULL CHECK (weight > 0)
                )
            ''')
            self._update_flag('db_version', '2')
        if self.version == 2:
            log.debug('Migrating from version 2 to version 3')
            self._u('''
                CREATE TABLE library_credentials (
                    id UUID PRIMARY KEY,
                    library TEXT NOT NULL,
                    username TEXT NOT NULL,
                    password TEXT NOT NULL,
                    display_name TEXT NOT NULL
                )
            ''')
            self._update_flag('db_version', '3')
        if self.version == 3:
            log.debug('Migrating from version 3 to version 4')
            self._u('''
                CREATE TABLE library_books (
                    id UUID PRIMARY KEY,
                    credential_id UUID REFERENCES library_credentials (id) ON DELETE CASCADE,
                    title TEXT NOT NULL,
                    due DATE NOT NULL,
                    renewable BOOLEAN NOT NULL
                )
            ''')
            self._update_flag('db_version', '4')
        if self.version == 4:
            log.debug('Migrating from version 4 to version 5')
            self._u("ALTER TABLE library_books ADD COLUMN item_id TEXT NOT NULL DEFAULT ''")
            self._update_flag('db_version', '5')
        if self.version == 5:
            log.debug('Migrating from version 5 to version 6')
            self._u("ALTER TABLE library_books ADD COLUMN medium TEXT NOT NULL DEFAULT ''")
            self._update_flag('db_version', '6')
        if self.version == 6:
            log.debug('Migrating from version 6 to version 7')
            self._u('''
                CREATE TABLE movie_people (
                    id UUID PRIMARY KEY,
                    person TEXT NOT NULL
                )
            ''')
            self._u('''
                CREATE TABLE movie_picks (
                    id UUID PRIMARY KEY,
                    pick_date DATE NOT NULL,
                    person_id UUID REFERENCES movie_people (id) ON DELETE SET NULL,
                    pick_text TEXT NOT NULL
                )
            ''')
            self._update_flag('db_version', '7')
        if self.version == 7:
            log.debug('Migrating from version 7 to version 8')
            self._u('''
                CREATE TABLE electricity (
                    bill_date DATE PRIMARY KEY,
                    kwh INTEGER NOT NULL,
                    charge INTEGER NOT NULL,
                    bill INTEGER NOT NULL
                )
            ''')
            self._update_flag('db_version', '8')
        if self.version == 8:
            log.debug('Migrating from version 8 to version 9')
            self._u('''
                CREATE TABLE timeline_entries (
                    id UUID PRIMARY KEY,
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    description TEXT NOT NULL,
                    zoom_level INTEGER NOT NULL DEFAULT 1,
                    tags TEXT
                )
            ''')
            self._update_flag('db_version', '9')
        if self.version == 9:
            log.debug('Migrating from version 9 to version 10')
            self._u('''
                ALTER TABLE library_credentials
                ADD COLUMN balance INTEGER NOT NULL DEFAULT 0
            ''')
            self._update_flag('db_version', '10')
        if self.version == 10:
            log.debug('Migrating from version 10 to version 11')
            self._u('''
                CREATE TABLE schema_versions (
                    schema_version INTEGER PRIMARY KEY,
                    migration_date TIMESTAMP NOT NULL
                )
            ''')
            self._u('''
                CREATE TABLE captains_log (
                    id UUID PRIMARY KEY,
                    log_timestamp TIMESTAMP NOT NULL,
                    log_text TEXT NOT NULL
                )
            ''')
            self._delete_flag('db_version')
            self._add_schema_version(11)
        if self.version == 11:
            log.debug('Migrating from version 11 to version 12')
            self._u('''
                CREATE TABLE gas_prices (
                    id UUID PRIMARY KEY,
                    price_date DATE NOT NULL,
                    price NUMERIC NOT NULL,
                    gallons NUMERIC,
                    location TEXT,
                    vehicle TEXT,
                    miles_driven NUMERIC
                )
            ''')
            self._add_schema_version(12)

    def _insert_flag(self, flag_name: str, flag_value: str):
        sql = 'INSERT INTO flags (flag_name, flag_value) VALUES (%(flag_name)s, %(flag_value)s)'
        params = {'flag_name': flag_name, 'flag_value': flag_value}
        self._u(sql, params)

    def _delete_flag(self, flag_name: str):
        sql = 'DELETE FROM flags WHERE flag_name = %(flag_name)s'
        params = {'flag_name': flag_name}
        self._u(sql, params)

    def _update_flag(self, flag_name: str, flag_value: str):
        sql = 'UPDATE flags SET flag_value = %(flag_value)s WHERE flag_name = %(flag_name)s'
        params = {'flag_name': flag_name, 'flag_value': flag_value}
        self._u(sql, params)

    def _add_schema_version(self, schema_version: int):
        sql = '''
            INSERT INTO schema_versions (schema_version, migration_date)
            VALUES (%(schema_version)s, %(migration_date)s)
        '''
        self._u(sql, {'schema_version': schema_version, 'migration_date': datetime.datetime.utcnow()})

    def _table_exists(self, table_name: str) -> bool:
        sql = 'SELECT count(*) table_count FROM information_schema.tables WHERE table_name = %(table_name)s'
        for record in self._q(sql, {'table_name': table_name}):
            if record['table_count'] == 0:
                return False
        return True

    @property
    def version(self):
        if self._table_exists('schema_versions'):
            sql = 'SELECT max(schema_version) current_version FROM schema_versions'
            for record in self._q(sql):
                return record['current_version']
        if self._table_exists('flags'):
            sql = 'SELECT flag_value FROM flags WHERE flag_name = %(flag_name)s'
            for record in self._q(sql, {'flag_name': 'db_version'}):
                return int(record['flag_value'])
        return 0
