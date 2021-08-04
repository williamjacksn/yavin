import datetime
import fort


class ExpensesDatabase(fort.SQLiteDatabase):
    def get_expenses(self, account_prefix: str, start_date: datetime.date, end_date: datetime.date):
        sql = '''
            select
                a.full_name account, t.post_date, t.description, s.memo,
                (s.value_num / cast(s.value_denom as real)) amount
            from splits s
            left join v_account_full_names a on a.guid = s.account_guid
            left join transactions t on t.guid = s.tx_guid
            where t.post_date between :start_date and :end_date
            and a.full_name like :account_prefix
            order by t.post_date
        '''
        params = {
            'account_prefix': account_prefix,
            'start_date': start_date,
            'end_date': end_date
        }
        return self.q(sql, params)
