import os
import mysql.connector
import telebot
import time
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
            ним в диалог, задавая подходящие вопросы о его проблеме. Задай много вопросов, чтобы собрать побольше деталей. 
            После того, как ты подробно опросишь паицента, твоя задача указать возможные причины для состояния пациента и посоветовать
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
            content="""Ты - суммаризатор. Тебе на вход даются жалобы и симптомы пациента. 
            Твоя задача кратко, но сохраня все фактические детали, проссумировать переданную пациентом информацию
            о его состоянии. Текст должен быть сжатым. Не используй в тексте слова "пациент" или "у вас". 
            Например, вместо "Пациент жалуется на трёхдневную боль в горле" или
            "У вас три дня болит горло", напиши "Три дня боль в горле." 
            Не указывай возможные причины. Не указывай рекомендации. Только информацию и симптомы, содержащиеся в исходном тексте. 
            Каждый твой ответ должен оканчиваться двумя символами ##. 
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
user_curr_case = {}



#                               """GLOBAL CHAT-MANAGING FUNCTIONS"""

def set_user_state(user_id, state):
    user_state[user_id] = state

def get_user_state(user_id):
    return user_state.get(user_id, None)

def set_user_memory(user_id, memory):
    user_memory[user_id] = memory

def get_user_memory(user_id):
    return user_memory.get(user_id, default_memory)

def set_user_curr_case(user_id, case_id):
    user_curr_case[user_id] = case_id

def get_user_curr_case(user_id):
    return user_curr_case.get(user_id, None)

def generate_case_id(user_id):
    num_cases = functions.get_item_from_table_by_key('num_cases', 'users', 'user_id', user_id)

    if num_cases is None:
        num_cases = 1

    try:
        num_cases = int(num_cases) + 1
    except ValueError:
        print(f"Invalid num_cases value for user_id: {user_id}")
        return None

    return f"{user_id}_{num_cases}"

    
def conversation_step(message, memory=default_memory):
    bot_instance = ChatBot(llm, prompt, memory)

    bot.send_chat_action(message.chat.id, 'typing')
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

    button_1 = types.InlineKeyboardButton("Да, всё супер!", callback_data='share_case')
    button_2 = types.InlineKeyboardButton("Хочу изменить", callback_data='edit_case')

    keyboard.add(button_1, button_2)

    return keyboard

def add_photo_menu():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row_width = 1

    button_1 = types.InlineKeyboardButton("Да", callback_data='add_photo')
    button_2 = types.InlineKeyboardButton("Нет", callback_data='no_photo')

    keyboard.add(button_1, button_2)

    return keyboard

def summarize_into_case(memory):
    summarizer_instance = Summarizer(llm, summarizer_prompt, memory)
    return summarizer_instance.summarize(memory)

def save_photo(message):
    file_id = message.photo[-1].file_id
    file_info = bot.get_file(file_id)
    downloaded_file = bot.download_file(file_info.file_path)

    case_id = get_user_curr_case(message.chat.id)
    file_path = save_image_to_server(downloaded_file, message.chat.id, case_id)
    
    # ... 




#                                    """/-COMMAND HANDLERS""" 

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.chat.id
    user_name = functions.get_item_from_table_by_key('user_name', 'users', 'user_id', user_id)
    set_user_memory(user_id, default_memory)
    
    if user_name:
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

    functions.add_user_name(user_id, user_name)  

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
    bot.send_chat_action(message.chat.id, 'typing')
    case = summarize_into_case(memory=get_user_memory(message.chat.id))

    set_user_memory(message.chat.id, case)
    case_id = generate_case_id(message.chat.id)
    set_user_curr_case(message.chat.id, case_id)
    functions.add_user_case(case_id, f'Кейс {int(time.time())}', message.chat.id, 'started', case)
    functions.increment_value('users', 'num_cases', 'user_id', message.chat.id)
    bot.send_message(message.chat.id, functions.get_item_from_table_by_key('case_id', 'user_cases', 'user_id', message.chat.id))
    bot.send_message(message.chat.id, case_id)

    bot.send_message(message.chat.id, case)
    bot.send_message(message.chat.id, 'Хотите прикрепить фото симптомов?', reply_markup=add_photo_menu())
    



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
    memory = default_memory
    case = get_user_memory(message.chat.id)
    memory.save_context({"input": case}, {"output": "Что бы Вы хотели изменить или добавить?"}) 
    memory.save_context({"input": message.text}, {"output": "Сейчас внесу изменения!"})

    bot.send_message(message.chat.id, 'Вот обновлённая версия:')
    bot.send_chat_action(message.chat.id, 'typing')
    case = summarize_into_case(memory)
    bot.send_message(message.chat.id, case)
    set_user_memory(message.chat.id, case)

    bot.send_message(message.chat.id, 'Отправляю врачу?', reply_markup=share_case_menu())

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == 'sending_photos'
                                            and not message.text.startswith('/'))
def handle_photos(message):
    save_photo(message)
    bot.send_message(message.chat.id, 'Получил!')
    # compile case





#                                    """CALLBACK HANDLERS"""

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    if call.data == 'new_case':
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        memory = default_memory
        memory.save_context({'input': 'Начнём.'}, {'output': 'Начинаем новый кейс. Какие у вас жалобы?'})
        set_user_memory(call.message.chat.id, memory)
        bot.send_message(call.message.chat.id, "Начинаем новый кейс. Введите /sharecase, когда захотите поделиться им с врачом.")
        bot.send_message(call.message.chat.id, "Какие у вас жалобы?")
        set_user_state(call.message.chat.id, 'creating_case')
        
    elif call.data == 'my_cases':
        bot.delete_message(chat_id=call.message.chat.id,
                              message_id=call.message.message_id)
        bot.send_message(call.message.chat.id, "Мои кейсы:")

    elif call.data == 'share_case':
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        # RESET MEMORY
        # bot.send_message(get_user_doctor(call.message.chat.id), get_user_memory(call.message.chat.id))
        bot.send_message(call.message.chat.id, 'Отправил врачу! Он скоро с Вами свяжется.')

    elif call.data == 'edit_case':
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        bot.send_message(call.message.chat.id, 'Что бы Вы хотели изменить или добавить?')
        set_user_state(call.message.chat.id, 'editing_case')
    
    elif call.data == 'add_photo':
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        bot.send_message(call.message.chat.id, 'Отправляйте фотографии! (по одной)')
        set_user_state(call.message.chat.id, 'sending_photos')

    elif call.data == 'no_photo':
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        bot.send_message(call.message.chat.id, 'Утвердите кейс перед тем, как я поделюсь им с врачом.', reply_markup=share_case_menu())




#                                    """PHOTO HANDLER"""
@bot.message_handler(content_types=['photo'])
def handle_photos(message):
    user_state = get_user_state(user_id)

    if user_state == 'sending_photos':
        save_photo(message)
        bot.send_message(message.chat.id, 'Получил!')


    else:
        bot.send_message(user_id, "Кажется, сейчас не самый подходящий момент для этого.")
    # Optionally, store file_path in your MySQL database
    # ...


bot.infinity_polling()
