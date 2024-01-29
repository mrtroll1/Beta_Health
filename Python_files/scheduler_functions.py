import asyncio
import datetime
import apscheduler 
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from chat_bot import bot

scheduler = AsyncIOScheduler()

async def send_scheduled_message(chat_id, message):
    await bot.send_message(chat_id, message)

async def schedule_message(chat_id, message, delay_in_hours=0, delay_in_minutes=0, delay_in_seconds=15):
    scheduled_time = datetime.datetime.now() + datetime.timedelta(seconds=delay_in_seconds, minutes=delay_in_minutes, hours=delay_in_hours)
    await bot.send_message(chat_id, f'Отправка сообщения запланированна на {scheduled_time}')
    scheduler.add_job(func=send_scheduled_message, name='send_scheduled_message', trigger='date', run_date=scheduled_time, args=[chat_id, message])







