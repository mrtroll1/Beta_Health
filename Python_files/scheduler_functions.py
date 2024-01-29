import apscheduler 
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import datetime
import asyncio
from chat_bot import bot 

scheduler = AsyncIOScheduler()
scheduler.start()

async def send_scheduled_message(chat_id, message):
    await bot.send_message(chat_id, message)

async def schedule_message(chat_id, message, delay_in_hours=0, delay_in_minutes=0, delay_in_seconds=15):
    await bot.send_message(chat_id, 'entered schedule_message function')
    schedule_time = datetime.datetime.now() + datetime.timedelta(seconds=delay_in_seconds, minutes=delay_in_minutes, hours=delay_in_hours)
    scheduler.add_job(send_scheduled_message, 'date', run_date=schedule_time, args=[chat_id, message])






