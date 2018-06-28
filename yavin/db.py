import logging
import psycopg2
import psycopg2.extras
import uuid

log = logging.getLogger(__name__)
psycopg2.extras.register_uuid()


class YavinDatabase:
    def __init__(self, connection_string):
        self.cnx = psycopg2.connect(connection_string, cursor_factory=psycopg2.extras.RealDictCursor)
        self.cnx.autocommit = True

    def _q(self, sql, args=None):
        if args is None:
            args = []
        with self.cnx.cursor() as c:
            c.execute(sql, args)
            while True:
                try:
                    row = c.fetchone()
                except psycopg2.ProgrammingError as e:
                    log.error(e)
                    return
                if row is None:
                    return
                yield row

    def _q_one(self, sql, args=None):
        for row in self._q(sql, args):
            return row
        return None

    def _u(self, sql, args=None):
        if args is None:
            args = []
        with self.cnx.cursor() as c:
            c.execute(sql, args)
            return c.rowcount

    # jar

    def add_jar_entry(self, entry_date):
        last = self._q_one('SELECT MAX(id) id FROM jar_entries')
        params = {
            'id': last['id'] + 1,
            'entry_date': entry_date
        }
        self._u('INSERT INTO jar_entries (id, entry_date) VALUES (%(id)s, %(entry_date)s)', params)

    def get_recent_jar_entries(self, limit=10):
        params = {'limit': limit}
        yield from self._q('SELECT id, entry_date FROM jar_entries ORDER BY entry_date DESC LIMIT %(limit)s', params)

    # library

    def add_library_credential(self, params):
        params['id'] = uuid.uuid4()
        self._u('''
            INSERT INTO library_credentials (id, library, username, password, display_name)
            VALUES (%(id)s, %(library)s, %(username)s, %(password)s, %(display_name)s)
        ''', params)

    def get_library_credentials(self):
        sql = 'SELECT id, library, username, password, display_name, balance FROM library_credentials'
        return list(self._q(sql))

    def delete_library_credential(self, params):
        self._u('DELETE FROM library_credentials WHERE id = %(id)s', params)

    def update_balance(self, params):
        self._u('UPDATE library_credentials SET balance = %(balance)s WHERE id = %(id)s', params)

    def add_library_book(self, params):
        params['id'] = uuid.uuid4()
        sql = '''
            INSERT INTO library_books (id, credential_id, title, due, renewable, item_id, medium)
            VALUES (%(id)s, %(credential_id)s, %(title)s, %(due)s, %(renewable)s, %(item_id)s, %(medium)s)
        '''
        self._u(sql, params)

    def update_due_date(self, params):
        sql = 'UPDATE library_books SET due = %(due)s WHERE item_id = %(item_id)s'
        return self._u(sql, params)

    def clear_library_books(self):
        self._u('DELETE FROM library_books')

    def get_book_credentials(self, params):
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

    def add_weight_entry(self, entry_date, weight):
        try:
            self._u('INSERT INTO weight_entries (entry_date, weight) VALUES (%s, %s)', [entry_date, weight])
        except psycopg2.IntegrityError:
            return 'There is already a weight entry for {}.'.format(entry_date)

    def get_recent_weight_entries(self, limit=10):
        yield from self._q('SELECT entry_date, weight FROM weight_entries ORDER BY entry_date DESC LIMIT %s', [limit])

    def get_weight_most_recent(self):
        row = self._q_one('SELECT weight FROM weight_entries ORDER BY entry_date DESC')
        return row['weight']

    # movie night

    def add_movie_night_person(self, params):
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

    def add_movie_night_pick(self, params):
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

    def add_electricity(self, params):
        sql = '''
            INSERT INTO electricity (bill_date, kwh, charge, bill)
            VALUES (%(bill_date)s, %(kwh)s, %(charge)s, %(bill)s)
        '''
        self._u(sql, params)

    def get_electricity(self):
        sql = 'SELECT bill_date, kwh, charge, bill FROM electricity'
        return self._q(sql)

    def migrate(self):
        log.debug('Checking for database migrations')
        if self.version == 0:
            log.debug('Migrating from version 0 to version 1')
            self._u('''
                CREATE TABLE flags (
                    flag_name TEXT PRIMARY KEY,
                    flag_value TEXT NOT NULL
                )
            ''')
            self._u('INSERT INTO flags (flag_name, flag_value) VALUES (%s, %s)', ['db_version', '1'])
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
            self._u('UPDATE flags SET flag_value = %s WHERE flag_name = %s', ['2', 'db_version'])
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
            self._u('UPDATE flags SET flag_value = %s WHERE flag_name = %s', ['3', 'db_version'])
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
            self._u('UPDATE flags SET flag_value = %s WHERE flag_name = %s', ['4', 'db_version'])
        if self.version == 4:
            log.debug('Migrating from version 4 to version 5')
            self._u("ALTER TABLE library_books ADD COLUMN item_id TEXT NOT NULL DEFAULT ''")
            self._u('UPDATE flags SET flag_value = %s WHERE flag_name = %s', ['5', 'db_version'])
        if self.version == 5:
            log.debug('Migrating from version 5 to version 6')
            self._u("ALTER TABLE library_books ADD COLUMN medium TEXT NOT NULL DEFAULT ''")
            self._u('UPDATE flags SET flag_value = %s WHERE flag_name = %s', ['6', 'db_version'])
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
            self._u('UPDATE flags SET flag_value = %s WHERE flag_name = %s', ['7', 'db_version'])
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
            self._u('UPDATE flags SET flag_value = %s WHERE flag_name = %s', ['8', 'db_version'])
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
            self._u('UPDATE flags SET flag_value = %s WHERE flag_name = %s', ['9', 'db_version'])
        if self.version == 9:
            log.debug('Migrating from version 9 to version 10')
            self._u('''
                ALTER TABLE library_credentials
                ADD COLUMN balance INTEGER NOT NULL DEFAULT 0
            ''')
            self._u('UPDATE flags SET flag_value = %s WHERE flag_name = %s', ['10', 'db_version'])

    @property
    def version(self):
        try:
            row = self._q_one('SELECT flag_value FROM flags WHERE flag_name = %s', ['db_version'])
        except psycopg2.ProgrammingError as e:
            if e.diag.message_primary == 'relation "flags" does not exist':
                return 0
            raise
        return int(row['flag_value'])
