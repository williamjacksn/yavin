import datetime


def clean_due_date(due):
    return datetime.datetime.strptime(due, '%m\u2011%d\u2011%Y').date()


def in_two_minutes():
    return datetime.datetime.now() + datetime.timedelta(minutes=2)


def str_to_date(d):
    return datetime.datetime.strptime(d, '%Y-%m-%d').date()


def today():
    return datetime.date.today()
