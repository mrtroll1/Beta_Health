import os
import mysql.connector
import telebot
from telebot import types
from bots import ChatBot, Summarizer
# import functions
from langchain.prompts import ChatPromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
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
            content="""Ты - виртаульный ассистент врача. Твоя задача принять жалобу или вопрос от пациента и вступить с 
            ним в диалог, задавая подходящие вопросы о его проблеме. После того, как ты подробно опросишь паицента, 
            твоя задача указать возможные причины для состояния пациента и посоветовать
            методы лечения, у которых известный уровень доказанности. 
            Обращайся к пациенту на Вы. Если какой-то вопрос или сообщение от пациента не соотвествует
            тематике здравоохранения, то напомни ему об этом. Старайся писать не очень длинные сообщения."""
        ),  
        MessagesPlaceholder(
            variable_name="chat_history"
        ),  
        HumanMessagePromptTemplate.from_template(
            "{human_input}"
        ),  
    ]
)

summarizer_prompt = ChatPromptTemplate.from_messages(
    [
        SystemMessage(
            content="""Тебе на вход даётся диалог пациента (Human) и ассистента (AI). 
            Твоя задача кратко, но сохраня все фактические детали, проссумировать переданную пациентом информацию
            о его состоянии и сипмтомах и скомпоновать её в текст. 
            Текст должен быть сжатым.
            Не используй в тексте слова пациент. Например, вместо "Пациент жалуется на трёхдневную боль в горле", 
            напиши "Три дня боль в горле."
            Не надо включать рекомендации.
            Не надо включать диагноз / возможные причины.
            Только информацию о симптомах.
            """
        ),  
        MessagesPlaceholder(
            variable_name="chat_history"
        ),  
        HumanMessagePromptTemplate.from_template(
            "{human_input}"
        ),  
    ]
)

default_memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

bot = telebot.TeleBot(telegram_api_token)

user_state = {}



#                               """GLOBAL CHAT-MANAGING FUNCTIONS"""

def set_user_state(user_id, state):
    user_state[user_id] = state

def get_user_state(user_id):
    return user_state.get(user_id, None)
    
def keep_conversation(message, memory=default_memory):
    bot_instance = ChatBot(llm, prompt, default_memory)
    response = bot_instance.process_message(message.text)
    bot.send_message(message.chat.id, response)
    bot.register_next_step_handler(message, lambda msg: keep_conversation(msg, bot_instance))

def main_menu(message):
    keyboard = types.InlineKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)

    button_1 = types.InlineKeyboardButton("Новый кейс")
    button_2 = types.InlineKeyboardButton("Мои кейсы")
    button_3 = types.InlineKeyboardButton("...")

    keyboard.add(button_1, button_2, button_3)

    bot.send_message(message.chat.id, "Как могу помочь?", reply_markup=keyboard)
    set_user_state(message.from_user.id, 'awaiting_menu_choice')



#                                    """/-COMMAND HANDLERS"""

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.chat.id
    user_name = 'Барак Обама'
    bot.send_message(user_id, "We're live babyyy", reply_markup=None)
    # user_name = functions.get_item_from_table_by_key('user_names', 'user_name', 'user_id', user_id)
    
    if user_name is not None:
        welcome_msg = f"Здравствуйте, {user_name}!"
        bot.send_message(user_id, welcome_msg)
        main_menu(message)
        
    else:
        welcome_msg = "Добро пожаловать на Beta-Health! Как я могу к Вам обращаться?"
        bot.send_message(user_id, welcome_msg)
        bot.register_next_step_handler(message, handle_name_input)

def handle_name_input(message):
    user_id = message.chat.id
    user_name = message.text  

    # functions.add_user_name(user_id, user_name)  

    confirmation_msg = f"Очень приятно, {user_name}! Сейчас я расскажу, как всё работает..."
    bot.send_message(user_id, confirmation_msg)

@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = "Вот доступные команды:\n"
    commands_list = [
        "/start - Запуск",
        "/menu - Главное меню",
        "/info - Информация",
        "/help - Показать это сообщение"
    ]
    help_text += '\n'.join(commands_list)
    bot.send_message(message.chat.id, help_text)

@bot.message_handler(commands=['menu'])
def menu(message):
    main_meanu(message)

@bot.message_handler(commands=['info'])
def send_info(message):
    info = 'Вот как всё работает ...'
    bot.send_message(message.chat.id, info)
    # ... введите /menu, чтобы начать пользоваться



#                                    """STATE HANDLERS"""

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == 'awaiting_menu_choice')
def handle_menu_choice(message):
    if message.text in ["Новый кейс", "Мои кейсы"]:
        bot.send_message(message.chat.id, f"Вы выбрали {message.text}")
        # if message.text == ...:
            # set_user_state(message.from_user.id, message.text)  
    else:
        bot.send_message(message.chat.id, "Пожалуйста, выберите вариант из меню")

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == 'editing_case')
def handle_case(message):
    keep_conversation(message)
    pass

bot.polling()
