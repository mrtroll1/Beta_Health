import os
import mysql.connector
import telebot
from telebot import types
from chat_bot_module import ChatBot, ChatOpenAI, ChatPromptTemplate, ConversationBufferMemory
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import MessagesPlaceholder
from langchain.schema import SystemMessage
from langchain.prompts import HumanMessagePromptTemplate

openai_api_key = os.environ.get('OPENAI_API_KEY')
telegram_api_token = os.environ.get('TELEGRAM_API_TOKEN')

llm = ChatOpenAI(openai_api_key=openai_api_key)  

prompt = ChatPromptTemplate.from_messages(
    [
        SystemMessage(
            content="""Ты ИИ ассистент врача. Твоя задача принять жалобу или вопрос от пациента и вступить с 
            ним в диалог, получая ответы и поочерёдно задавая подходящие вопросы. Когда все вопросы будут заданы, 
            твоя задача попробовать поставить диагноз и посоветовать обратиться к врачу или наоборот
            успокоить пациента, предложив способы лечения с известный уровнем доказательности. 
            Обращайся к пациенту на Вы. Если какой-то вопрос или сообщение от пациента не соотвествует
            тематике здравоохранения, то напомни ему об этом. Старайся давать ответы, длиннее 10 предложений, 
            только если этого очень требует ситуация."""
        ),  
        MessagesPlaceholder(
            variable_name="chat_history"
        ),  
        HumanMessagePromptTemplate.from_template(
            "{human_input}"
        ),  
    ]
)

memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

bot_instance = ChatBot(llm, prompt, memory)

bot = telebot.TeleBot(telegram_api_token)

def get_item_from_table_by_key(table, item, key_column, key_value):
    db_connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="...",
        database="beta_health"
    )
    db_cursor = db_connection.cursor()

    query = f"SELECT {item} FROM {table} WHERE {key_column} = %s"
    db_cursor.execute(query, (key_value,))
    result = db_cursor.fetchone()
    
    db_cursor.close()
    db_connection.close()

    return result[0] if result else None

def add_user_name(user_id, user_name):
    db_connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="...",
        database="beta_health"
    )
    db_cursor = db_connection.cursor()
    
    query = "INSERT INTO user_names (user_id, user_name) VALUES (%s, %s)"
    
    db_cursor.execute(query, (user_id, user_name))
    
    db_connection.commit() 
    db_cursor.close()
    db_connection.close()
    
def main_inline_menu():
    markup = types.InlineKeyboardMarkup()
    button1 = types.InlineKeyboardButton("Начать новый кейс", callback_data="button1")
    button2 = types.InlineKeyboardButton("Мои кейсы", callback_data="button2")
    markup.add(button1, button2)
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.chat.id
    user_name = get_item_from_table_by_key('user_names', 'user_name', 'user_id', user_id)
    
    if user_name:
        welcome_msg = f"Здравствуйте, {user_name}! Как я могу Вам помочь?"
        markup = main_inline_menu()
        bot.send_message(user_id, welcome_msg, reply_markup=markup)
        
    else:
        welcome_msg = "Здравствуйте! Я виртуальный health-ассистент. Как я могу к Вам обращаться?"
        bot.send_message(user_id, welcome_msg)
        bot.register_next_step_handler(message, handle_name_input)

def handle_name_input(message):
    user_id = message.chat.id
    user_name = message.text  

    add_user_name(user_id, user_name)  

    confirmation_msg = f"Очень приятно! Давайте начнём Ваш первый кейс, {user_name}. На что жалуемся?"
    bot.send_message(user_id, confirmation_msg)
    
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    memory.save_context({'input' : f'Меня зовут {user_name}'}, {'output' : 'Очень приятно!'})
    bot_instance = ChatBot(llm, prompt, memory)
    bot.register_next_step_handler(message, lambda msg: keep_conversation(msg, bot_instance))
        
def start_conversation(message):
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    bot_instance = ChatBot(llm, prompt, memory)
    keep_conversation(message, bot_instance)
    bot.register_next_step_handler(message, lambda msg: keep_conversation(msg, bot_instance))
    
def keep_conversation(message, bot_instance):
    response = bot_instance.process_message(message.text)
    bot.send_message(message.chat.id, response)
    bot.register_next_step_handler(message, lambda msg: keep_conversation(msg, bot_instance))
    
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    
    if call.data == "Начать новый кейс":
        bot.answer_callback_query(call.id, "Сейчас посмотрим...")
        bot.register_next_step_handler(message, start_conversation(message))
        
    elif call.data == "Мои кейсы":
        bot.answer_callback_query(call.id, "Ой. Пока не реализовано.")

bot.polling()
