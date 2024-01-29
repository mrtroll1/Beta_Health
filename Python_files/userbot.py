from pyrogram import Client, filters
import os 

api_id = os.environ.get('TG_API_ID')  
api_hash = os.environ.get('TG_API_HASH')  

with Client("my_account", api_id, api_hash) as app:
    @app.on_message(filters.me & filters.text)
    def echo(client, message):
        message.reply_text(message.text)

app.run()