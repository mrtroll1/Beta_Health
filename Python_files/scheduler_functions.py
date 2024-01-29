import apscheduler 
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import datetime
import asyncio

scheduler = AsyncIOScheduler()
scheduler.start()

async def send_scheduled_message(bot, chat_id, message):
    await bot.send_message(chat_id, message)

async def schedule_message(bot, chat_id, message, delay_in_hours=0, delay_in_minutes=0, delay_in_seconds=15):
    schedule_time = datetime.datetime.now() + datetime.timedelta(seconds=delay_in_seconds, minutes=delay_in_minutes, hours=delay_in_hours)
    scheduler.add_job(send_scheduled_message, 'date', run_date=schedule_time, args=[bot, chat_id, message])






