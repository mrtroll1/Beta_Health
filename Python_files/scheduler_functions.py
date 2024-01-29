import asyncio
import datetime
import apscheduler 
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from chat_bot import bot

scheduler = AsyncIOScheduler()

async def send_scheduled_message(chat_id, message):
    await bot.send_message(chat_id, message)

async def schedule_message(chat_id, message, delay):
    scheduled_time = datetime.datetime.now() + delay
    await bot.send_message(chat_id, f'Отправка сообщения запланированна на {scheduled_time}')
    scheduler.add_job(func=send_scheduled_message, name=chat_id, trigger='date', run_date=scheduled_time, args=[chat_id, message])






