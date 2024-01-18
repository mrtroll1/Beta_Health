import os
import mysql.connector
import telebot
from telebot import types
from bots import ChatBot, Summarizer
import functions
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
            Обращайся к пациенту на Вы (с большой буквы). Если какой-то вопрос или сообщение от пациента не соотвествует
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
user_memory = {}
user_doctor = {}



#                               """GLOBAL CHAT-MANAGING FUNCTIONS"""

def set_user_state(user_id, state):
    user_state[user_id] = state

def get_user_state(user_id):
    return user_state.get(user_id, None)

def set_user_memory(user_id, memory):
    user_memory[user_id] = memory

def get_user_memory(user_id):
    return user_memory.get(user_id, None)

def set_user_doctor(user_id, doctor):
    user_doctor[user_id] = memory

def get_user_doctor(user_id):
    return user_doctor.get(user_id, None)
    
def conversation_step(message, memory=default_memory):
    bot_instance = ChatBot(llm, prompt, memory)

    response = bot_instance.process_message(message.text)
    bot.send_message(message.chat.id, response)

    set_user_memory(message.chat.id, memory)

def main_menu():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row_width = 1

    button_1 = types.InlineKeyboardButton("Новый кейс", callback_data='new_case')
    button_2 = types.InlineKeyboardButton("Мои кейсы", callback_data='my_cases')

    keyboard.add(button_1, button_2)

    return keyboard

def share_case_menu():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row_width = 1

    button_1 = types.InlineKeyboardButton("Всё супер!", callback_data='share_case')
    button_2 = types.InlineKeyboardButton("Хочу изменить", callback_data='edit_case')

    keyboard.add(button_1, button_2)

    return keyboard

def summarize_into_case(memory):
    summarizer_instance = Summarizer(llm, summarizer_prompt, memory)
    return summarizer_instance.summarize(memory)



#                                    """/-COMMAND HANDLERS""" 

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.chat.id
    user_name = 'Обама'
    # user_name = functions.get_item_from_table_by_key('user_names', 'user_name', 'user_id', user_id)
    
    if user_name == 'Обама':
        welcome_msg = f"Здравствуйте, {user_name}!"
        bot.send_message(user_id, welcome_msg)
        bot.send_message(user_id, "Как могу помочь?", reply_markup=main_menu())
        set_user_state(message.from_user.id, 'awaiting_menu_choice')
        
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
    help_text = """Подробно о работе бота можно почитать по команде /info. \n 
                    Быть безупречным ботом непросто. Хотите связаться со службой поддержки?"""
    bot.send_message(message.chat.id, help_text)

@bot.message_handler(commands=['menu'])
def show_main_menu(message):
    bot.send_message(message.chat.id, 'Вот!', reply_markup=main_menu())

@bot.message_handler(commands=['info'])
def send_info(message):
    info = 'Вот как всё работает ...'
    bot.send_message(message.chat.id, info)
    # ... введите /menu, чтобы начать пользоваться

@bot.message_handler(commands=['sharecase'])
def send_to_doctor(message):
    case = summarize_into_case(memory=get_user_memory(message.chat.id))
    set_user_memory(message.chat.id, case)
    bot.send_message(message.chat.id, case)
    bot.send_message(message.chat.id, 'Утвердите кейс перед тем, как я поделюсь им с врачом.', reply_markup=share_case_menu())
    



#                                    """STATE HANDLERS"""

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == 'awaiting_menu_choice'
                                            and not message.text.startswith('/'))
def handle_menu_choice(message):
    bot.send_message(message.chat.id, "Пожалуйста, выберите вариант из меню")

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == 'creating_case'
                                            and not message.text.startswith('/'))
def handle_message(message):
    conversation_step(message, get_user_memory(message.chat.id))

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == 'editing_case'
                                            and not message.text.startswith('/'))
def edit_case(message):
    memory = defualt_memory
    case = get_user_memory(message.chat.id)
    memory.save_context({"input": f"Хочу изменить следующий кейс: {case}"}, {"output": "Что бы Вы хотели изменить или добавить?"}) 
    memory.save_context({"input": f"{message.text}"}, {"output": "Сейчас внесу изменения!"})
    bot.send_message(message.chat.id, 'Вот обновлённая версия:')
    bot.send_message(message.chat.id, summarize_into_case(memory))


    
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    if call.data == 'new_case':
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        memory = default_memory
        memory.save_context({"input": "Начнём."}, {"output": "Начинаем новый кейс. Какие у вас жалобы?"})
        set_user_memory(call.message.chat.id, memory)
        bot.send_message(call.message.chat.id, "Начинаем новый кейс. Какие у вас жалобы?")
        set_user_state(call.message.chat.id, 'creating_case')
        
    elif call.data == 'my_cases':
        # Action for button 2
        bot.deleted_message(chat_id=call.message.chat.id,
                              message_id=call.message.message_id)
        bot.send_message(call.message.chat.id, "Мои кейсы:")

    elif call.data == 'share_case':
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        # bot.send_message(get_user_doctor(call.message.chat.id), get_user_memory(call.message.chat.id))
        bot.send_message(call.message.chat.id, 'Отправил врачу! Он скоро с Вами свяжется.')

    elif call.data == 'edit_case':
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        bot.send_message(call.message.chat.id, 'Что бы Вы хотели изменить или добавить?')


bot.infinity_polling()
