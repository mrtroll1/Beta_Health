import asyncio
import datetime
import apscheduler 
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from chat_bot import bot, scheduler

async def send_scheduled_message(chat_id, message):
    await bot.send_message(chat_id, message)

async def schedule_message(chat_id, message, delay=datetime.timedelta(seconds=10)):
    await bot.send_message(chat_id, 'entered schedule_message function')
    scheduled_time = datetime.datetime.now() + delay
    await bot.send_message(chat_id, f'Отправка сообщения запланированна на {scheduled_time}')
    try:
        scheduler.add_job(func=send_scheduled_message, trigger='date', run_date=scheduled_time, args=[chat_id, message])
    except:
        bot.send_message(chat_id, f'Could not schedule a job with args: {chat_id}, {message}, {delay}')






