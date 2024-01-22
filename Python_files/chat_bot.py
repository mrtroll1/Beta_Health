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
            ним в диалог, задавая подходящие вопросы о его проблеме. Задай как можно больше вопросов, чтобы собрать побольше деталей. 
            Получи следующую информацию: начало, локализация, продолжительность, характер, облегчающие/усугубляющие факторы, 
            временная закономерность, интенсивность, история похожих болезней/симптомов. 
            После того, как ты подробно опросишь паицента, твоя задача указать возможные причины для состояния пациента и посоветовать
            методы лечения, у которых известный уровень доказанности. Это сообщение должно оканчиваться двумя символами ##. 
            Обращайся к пациенту на Вы (с большой буквы). Если какой-то вопрос или сообщение от пациента не соотвествует
            тематике здравоохранения, то напомни ему об этом. Старайся писать не длинные сообщения."""
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
            content="""Тебе на вход даётся диалог ассистента AI и пациента Human. 
            Твоя задача, сохраня все фактические детали, проссумировать переданную пациентом информацию
            о его состоянии. Твой ответ доленж иметь две секции: жалобы и рекоммендации. Не используй в тексте слова "пациент" или "у вас". 
            Например, вместо "Пациент жалуется на трёхдневную боль в горле" или
            "У вас три дня болит горло", напиши "Три дня боль в горле." 
            Не указывай возможные причины. Не пиши рекомендации. Не задавай вопросов.
            Используй только информацию и симптомы, содержащиеся в ответах пациента. 
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
    return user_memory.get(user_id, ConversationBufferMemory(memory_key="chat_history", return_messages=True))

def set_user_curr_case(user_id, case_id):
    user_curr_case[user_id] = case_id

def get_user_curr_case(user_id):
    return user_curr_case.get(user_id, None)

def generate_case_id(user_id):
    num_cases = functions.get_item_from_table_by_key('num_cases', 'users', 'user_id', user_id)

    if num_cases is None:
        num_cases = 0

    try:
        num_cases = int(num_cases)
    except ValueError:
        print(f"Invalid num_cases value for user_id: {user_id}")
        return None

    return f"{user_id}_{num_cases}"

    
def conversation_step(message, memory):
    bot_instance = ChatBot(llm, prompt, memory)

    bot.send_chat_action(message.chat.id, 'typing')
    response = bot_instance.process_message(message.text)
    bot.send_message(message.chat.id, response)

    set_user_memory(message.chat.id, memory)

    symbol_combination = '##'
    if symbol_combination in response:
        bot.send_message(message.chat.id, 'Хотите прикрепить фото симптомов?', reply_markup=add_photo_menu())

    
def main_menu():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row_width = 1

    button_1 = types.InlineKeyboardButton("Новый кейс", callback_data='new_case')
    button_2 = types.InlineKeyboardButton("Мои кейсы", callback_data='my_cases')

    keyboard.add(button_1, button_2)

    return keyboard

def accept_case_menu():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row_width = 1

    button_1 = types.InlineKeyboardButton("Да, отправляй!", callback_data='finalize_case')
    button_2 = types.InlineKeyboardButton("Хочу изменить", callback_data='edit_case')
    butoon_3 = types.InlineKeyboardButton("Сохрани, но не отправляй врачу", callback_data='save_and_not_share')
    button_4 = types.InlineKeyboardButton("Не сохраняй и не отправляй врачу", callback_data='delete_and_not_share')

    keyboard.add(button_1, button_2)

    return keyboard

def add_photo_menu():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row_width = 1

    button_1 = types.InlineKeyboardButton("Да", callback_data='add_photo')
    button_2 = types.InlineKeyboardButton("Нет", callback_data='finalize_case')

    keyboard.add(button_1, button_2)

    return keyboard

def more_photos_menu():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row_width = 1

    button_1 = types.InlineKeyboardButton("Да", callback_data='more_photos')
    button_2 = types.InlineKeyboardButton("Нет", callback_data='finalize_case')

    keyboard.add(button_1, button_2)

    return keyboard

def quickstart_new_case_menu():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row_width = 1

    button_1 = types.InlineKeyboardButton("Начать новый кейс", callback_data='quickstart_new_case')

    keyboard.add(button_1, button_2)

    return keyboard

def summarize_into_case(memory): 
    summarizer_instance = Summarizer(llm, summarizer_prompt, memory)
    return summarizer_instance.summarize(memory)

def save_photo(message):
    if isinstance(message.photo, list) and message.photo:
        largest_photo = message.photo[-1]  
        file_id = largest_photo.file_id
    else:
        print("No photos found in the message.")
        return

    file_info = bot.get_file(file_id)
    downloaded_file = bot.download_file(file_info.file_path)

    case_id = get_user_curr_case(message.chat.id)
    case_specific_path, full_path = functions.save_image_to_server(downloaded_file, message.chat.id, case_id)

    functions.alter_table('user_cases', 'case_media_path', case_specific_path, 'case_id', case_id)

def compile_case(case_id, recepient):
    base_path = '/home/luka/Projects/Beta_Health/User_data/Cases'
    case_path = os.path.join(base_path, str(case_id))
    case_text = functions.get_item_from_table_by_key('case_data', 'user_cases', 'case_id', case_id)

    if not os.path.exists(case_path):
        print(f"No directory found for case ID {case_id}")
        return

    media_group = []
    for filename in os.listdir(case_path):
        if len(media_group) >= 10: 
            break

        file_path = os.path.join(case_path, filename)
        functions.decrypt_file(file_path)

        with open(file_path, 'rb') as file:
            media_group.append(types.InputMediaPhoto(file.read()))

        functions.encrypt_file(file_path)

    if media_group:
        bot.send_media_group(recepient, media_group)

    bot.send_message(recepient, case_text)




#                                    """/-COMMAND HANDLERS""" 

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.chat.id
    user_name = functions.get_item_from_table_by_key('user_name', 'users', 'user_id', user_id)
    set_user_memory(user_id, ConversationBufferMemory(memory_key="chat_history", return_messages=True))
    
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
    bot.register_next_step_handler(message, quickstart)

def quickstart(message):
    user_name = functions.get_item_from_table_by_key('user_name', 'users', 'user_id', message.chat.id)
    bot.send_message(message.chat.id, 'Моя задача - сделать Ваше взаимодействие с доктором проще и удобнее для обеих сторон.')
    bot.send_message(message.chat.id, 'Моя главная фишка - система \'кейсов\'. Кейс = жалобы и симптомы пациента + диагноз и рекоммендации врача.')
    bot.send_message(message.chat.id, """Первую часть кейса составляем мы с Вами вместе. Сценарий такой:
    Вы обращаетесь ко мне с жалобой; я задаю Вам уточняющие вопросы; Вы подробно на них отвечаете; из данных Вами ответов я составляю текст.
    При желании, вы прикрепляете медиафалы. Например, фото симптомов или медицинские справки (если уместно). """)
    bot.send_message(message.chat.id, 'Давайте попробуем! Сейчас я отправлю Вам меню, в котором всего одна кнопка.')
    bot.send_message(message.chat.id, 'Нажимайте!', reply_markup=quickstart_new_case_menu())
    set_user_state(message.chat.id, 'quickstarting')


@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = """Подробно о работе бота можно почитать по команде /info. 
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
    case = summarize_into_case(get_user_memory(message.chat.id))
    set_user_memory(message.chat.id, case)

    case_id = get_user_curr_case(message.chat.id)
    functions.add_user_case(case_id, f'Кейс {case_id}', message.chat.id, 'started', case)

    bot.send_message(message.chat.id, case_id)

    
    



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
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True) 
    case = get_user_memory(message.chat.id)
    memory.save_context({"input": case}, {"output": "Что бы Вы хотели изменить или добавить?"}) 
    memory.save_context({"input": message.text}, {"output": "Сейчас внесу изменения!"})

    bot.send_message(message.chat.id, 'Вот обновлённая версия:')
    bot.send_chat_action(message.chat.id, 'typing')
    case = summarize_into_case(memory)
    bot.send_message(message.chat.id, case)
    set_user_memory(message.chat.id, case)
    

    bot.send_message(message.chat.id, 'Отправляю врачу?', reply_markup=accept_case_menu())

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == 'sending_photos'
                                            and not message.text.startswith('/'))
def handle_photos(message):
    save_photo(message)
    bot.send_message(message.chat.id, 'Получил! Хотите отправить ещё фото?', reply_markup=more_photos_menu())




#                                    """CALLBACK HANDLERS"""

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    if call.data == 'new_case':
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        memory.save_context({'input': 'Начнём.'}, {'output': 'Начинаем новый кейс. Какие у вас жалобы?'})
        set_user_memory(call.message.chat.id, memory)

        functions.increment_value('users', 'num_cases', 'user_id', call.message.chat.id)
        case_id = generate_case_id(call.message.chat.id)
        set_user_curr_case(call.message.chat.id, case_id)
        functions.add_user_case(case_id, f'Кейс {case_id}', call.message.chat.id, 'started', '')

        bot.send_message(call.message.chat.id, case_id)

        bot.send_message(call.message.chat.id, "Начинаем новый кейс. Введите /sharecase, когда захотите поделиться им с врачом.")
        bot.send_message(call.message.chat.id, "Какие у вас жалобы?")
        set_user_state(call.message.chat.id, 'creating_case')
        
    elif call.data == 'my_cases':
        bot.delete_message(chat_id=call.message.chat.id,
                              message_id=call.message.message_id)
        bot.send_message(call.message.chat.id, "Список ваших кейсов:")
        bot.send_message(call.message.chat.id, functions.get_itmes_from_table_by_key('case_name', 'user_cases', 'user_id', call.message.chat.id))

    elif call.data == 'send_case_to_doctor':
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        # bot.send_message(get_user_doctor(call.message.chat.id), get_user_memory(call.message.chat.id))
        bot.send_message(call.message.chat.id, 'Отправил врачу! Он скоро с Вами свяжется.')

    elif call.data == 'edit_case':
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        bot.send_message(call.message.chat.id, 'Что бы Вы хотели изменить или добавить?')
        set_user_state(call.message.chat.id, 'editing_case')
    
    elif call.data == 'add_photo':
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        bot.send_message(call.message.chat.id, 'Отправляйте фотографии! (в общей сложности не больше 10)')
        set_user_state(call.message.chat.id, 'sending_photos')

    elif call.data == 'more_photos':
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        bot.send_message(call.message.chat.id, 'Присылайте следующие фото')
        set_user_state(call.message.chat.id, 'sending_photos')
        
    elif call.data == 'finalize_case':
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        bot.send_chat_action(call.message.chat.id, 'typing')

        case = summarize_into_case(get_user_memory(call.message.chat.id))
        set_user_memory(call.message.chat.id, case)
        case_id = get_user_curr_case(call.message.chat.id)

        functions.add_user_case(case_id, f'Кейс {case_id}', call.message.chat.id, 'started', case)

        compile_case(get_user_curr_case(call.message.chat.id), call.message.chat.id)
        bot.send_message(call.message.chat.id, 'Хотите поделиться этим кейсом с врачом?', reply_markup=accept_case_menu())
    
    elif call.data == 'quickstart_new_case':
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        bot.send_message(call.message.chat.id, 'Какие у Вас жалобы? (поделитесь реальной проблемой или подыграйте мне)') 
        



#                                    """PHOTO HANDLER"""
@bot.message_handler(content_types=['photo'])
def handle_photos(message):
    user_state = get_user_state(message.chat.id)

    if user_state == 'sending_photos':
        save_photo(message)
        bot.send_message(message.chat.id, 'Получил! Хотите отправить ещё фото?', reply_markup=more_photos_menu())

    else:
        bot.send_message(user_id, "Кажется, сейчас не самый подходящий момент для этого.")

bot.infinity_polling()
