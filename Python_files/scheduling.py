from datetime import datetime

def datetime_to_greeting(dt, name):
    hour = dt.hour

    if 5 <= hour < 12:
        return f'Доброе утро, {name}.'
    elif 12 <= hour < 18:
        return f'Добрый день, {name}.'
    else:
        return f'Добрый вечер, {name}.'

def final_scheduled_time(delay, range_minutes):
    random_minutes = random.randint(-range_minutes, range_minutes)
    random_timedelta = datetime.timedelta(minutes=random_minutes)
    return datetime.datetime.now() + delay + random_timedelta









