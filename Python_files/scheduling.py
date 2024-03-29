# This file contains minor functions that parse scheduling messages

from datetime import datetime
from datetime import timedelta
import random

def datetime_to_greeting(dt, name, language):
    hour = dt.hour

    if language == 'russian':
        if 5 <= hour < 12:
            return f'Доброе утро, {name}. '
        elif 12 <= hour < 18:
            return f'Добрый день, {name}. '
        else:
            return f'Добрый вечер, {name}. '
    elif language == 'english':
        if 5 <= hour < 12:
            return f'Good morning, {name}. '
        elif 12 <= hour < 18:
            return f'Good afternoon, {name}. '
        else:
            return f'Good evening, {name}. '

def final_scheduled_time(delay, range_minutes):
    random_minutes = random.randint(-range_minutes, range_minutes)
    random_timedelta = timedelta(minutes=random_minutes)
    return datetime.now() + delay + random_timedelta









