import os
import mysql.connector
import telebot
from telebot import types
from chat_bot_module import ChatBot, ChatPromptTemplate, ConversationBufferMemory
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import MessagesPlaceholder
from langchain.schema import SystemMessage
from langchain.prompts import HumanMessagePromptTemplate

openai_api_key = os.environ.get('OPENAI_API_KEY')
telegram_api_token = os.environ.get('TELEGRAM_API_TOKEN')

llm = langchain_openai.ChatOpenAI(openai_api_key=openai_api_key)  

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

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.chat.id
    
    welcome_msg = f"Здравствуйте! Как я могу Вам помочь?"
    bot.register_next_step_handler(message, start_conversation(message))

def start_conversation(message):
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    bot_instance = ChatBot(llm, prompt, memory)
    keep_conversation(message, bot_instance)
    bot.register_next_step_handler(message, lambda msg: keep_conversation(msg, bot_instance))

def keep_conversation(message, bot_instance):
    response = bot_instance.process_message(message.text)
    bot.send_message(message.chat.id, response)
    bot.register_next_step_handler(message, lambda msg: keep_conversation(msg, bot_instance))
    
