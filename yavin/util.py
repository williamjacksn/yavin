import datetime


def str_to_date(d):
    return datetime.datetime.strptime(d, '%Y-%m-%d').date()


def today():
    return datetime.date.today()
