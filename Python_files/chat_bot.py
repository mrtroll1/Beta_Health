import os
import time
import asyncio
import bots
import data_functions
import scheduling
import menus 
import mysql.connector
import datetime
import random
import apscheduler 
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler
import telebot
from telebot import types
from telebot.async_telebot import AsyncTeleBot
from langchain.prompts import ChatPromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import MessagesPlaceholder
from langchain.schema import SystemMessage
from langchain.prompts import HumanMessagePromptTemplate

telegram_api_token = os.environ.get('TELEGRAM_API_TOKEN')
bot = telebot.async_telebot.AsyncTeleBot(telegram_api_token, parse_mode='Markdown')
helpservice_telegram_id = os.environ.get('HELPSERVICE_TELEGRAM_ID')
mysql_apscheduler_url = os.environ.get('MYSQL_APSCHEDULER_URL')
jobstores = {
    'default': SQLAlchemyJobStore(url=mysql_apscheduler_url)
}
# scheduler = AsyncIOScheduler(jobstores=jobstores)
scheduler = AsyncIOScheduler()


user_state = {}
user_memory = {}
user_curr_case = {}


#                               """GLOBAL CHAT-MANAGING functions"""

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
    num_cases = data_functions.get_item_from_table_by_key('num_cases', 'users', 'user_id', user_id)

    if num_cases is None:
        num_cases = 0

    try:
        num_cases = int(num_cases)
    except ValueError:
        print(f"Invalid num_cases value for user_id: {user_id}")
        return None

    return f"{user_id}_{num_cases}", num_cases


def chatgpt_to_telegram_markdown(input_text):
    bold_transformed = input_text.replace('**', '*')

    italics_transformed = ''
    skip_next = False
    for i, char in enumerate(bold_transformed):
        if skip_next:
            skip_next = False
            continue

        if char == '*' and (i == 0 or bold_transformed[i-1] != '*') and (i == len(bold_transformed) - 1 or bold_transformed[i+1] != '*'):
            italics_transformed += '_'
        else:
            italics_transformed += char
            if char == '*':
                skip_next = True

    return italics_transformed
    
async def conversation_step(message, memory, language):
    user_id = message.chat.id
    bot_instance = bots.ChatBot(bots.llm, bots.chat_prompt, memory)

    await bot.send_chat_action(user_id, 'typing')
    response = bot_instance.process_message(message.text)
    response = chatgpt_to_telegram_markdown(response)
    await bot.send_message(user_id, response, parse_mode='Markdown')

    set_user_memory(user_id, memory)

    symbol_combination = '##'
    if symbol_combination in response:
        if get_user_state(user_id) == 'quickstarting':
            await bot.send_chat_action(user_id, 'typing')
            await asyncio.sleep(3)
            if language == 'russian':
                msg = 'Хотите прикрепить медиа? (например, фото симптомов или результаты анализов)'
            elif language == 'english':
                msg = 'Would you like to attach media? (for example, photo of symptoms or medical tests results)'
            await bot.send_message(user_id, msg, parse_mode='Markdown', reply_markup=menus.quickstart_add_document_menu(language))
            set_user_state(user_id, 'quickstart_sending_documents')
        else:
            if language == 'russian':
                msg = 'Хотите прикрепить медиа?'
            elif language == 'english':
                msg = 'Would you like to attach media?'
            await bot.send_message(user_id, msg, reply_markup=menus.add_document_menu(language))
            set_user_state(user_id, 'awaiting_menu_choice')


async def quickstart(message, language):
    user_id = message.chat.id
    set_user_state(user_id, 'quickstarting')

    await bot.send_chat_action(user_id, 'typing')
    await asyncio.sleep(3)
    if language == 'russian':
        msg = 'Вы обратитесь ко мне с жалобой или сипмтомами. Я подробно расспрошу Вас о проблеме и дам предварительные рекоммендации. Далее, при необходимости, передам дело в руки врача.'
    elif language == 'english':
        msg = 'You approach me with a medical complaint. I thoroughly question you about it and provide simple treatment recommendations. Then, if needed, I will transfer this data to your doctor.'
    await bot.send_message(user_id, msg, parse_mode='Markdown')

    await bot.send_chat_action(user_id, 'typing')
    await asyncio.sleep(7)
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    bio = data_functions.get_item_from_table_by_key('medical_bio', 'users', 'user_id', user_id)
    if language == 'russian':
        memory.save_context({'input': 'Начнём.'}, {'output': 'Какие у вас жалобы?'})
        start_msg = 'Давайте попробуем! Какие у Вас жалобы?'
    elif language == 'english':
        memory.save_context({'input': 'Let\'s begin.'}, {'output': 'What are your complaints?'})
        start_msg = 'So... What are your complaints?'
    set_user_memory(user_id, memory)

    data_functions.increment_value('users', 'num_cases', 'user_id', user_id)
    case_id, num_cases = generate_case_id(user_id)
    set_user_curr_case(user_id, case_id)
    data_functions.add_user_case(case_id, user_id, 'Active')
    await bot.send_message(user_id, start_msg) 

def summarize_into_case(memory): 
    summarizer_instance = bots.Summarizer(bots.llm, bots.summarizer_prompt, memory)
    summary = summarizer_instance.summarize(memory)
    return chatgpt_to_telegram_markdown(summary)

async def save_document(message):
    file_id = None
    file_extension = None
    original_file_name = None

    if isinstance(message.photo, list) and message.photo:
        largest_photo = message.photo[-1]
        file_id = largest_photo.file_id
        file_extension = 'jpg' 
        original_file_name = None

    elif isinstance(message.document, list):
        for doc in message.document:
            file_id = doc.file_id
            file_name = doc.file_name
            file_extension = file_name.split('.')[-1] if '.' in file_name else None
            original_file_name = os.path.splitext(doc.file_name)[0]

    elif message.document:
        file_id = message.document.file_id
        file_name = message.document.file_name
        file_extension = file_name.split('.')[-1] if '.' in file_name else None
        original_file_name = os.path.splitext(message.document.file_name)[0]

    if not file_id:
        await bot.send_message(recipient, 'This file type is not supported')
        return

    file_info = await bot.get_file(file_id)
    downloaded_file = await bot.download_file(file_info.file_path)

    case_id = get_user_curr_case(message.chat.id)
    case_specific_path, full_path = data_functions.save_file_to_server(downloaded_file, message.chat.id, case_id, original_file_name, file_extension)

    data_functions.alter_table('user_cases', 'case_media_path', case_specific_path, 'case_id', case_id)

async def compile_case(case_id, recipient):
    base_path = '/home/luka/Projects/Beta_Health/User_data/Cases'
    case_path = os.path.join(base_path, str(case_id))
    case_text = data_functions.get_item_from_table_by_key('case_data', 'user_cases', 'case_id', case_id)

    if not os.path.exists(case_path):
        await bot.send_message(recipient, 'Data not found')
        return

    photo_group = []
    document_paths = []
    document_names = []
    for filename in os.listdir(case_path):
        if len(photo_group) + len(document_paths) >= 10: 
            await bot.send_message(recipient, 'Only first 10 files will be sent')
            break

        file_path = os.path.join(case_path, filename)
        file_extension = os.path.splitext(filename)[1].lower()
        document_names.append(filename[:-14] + file_extension)

        if file_extension in ['.jpg', '.jpeg', '.png']:
            data_functions.decrypt_file(file_path)
            with open(file_path, 'rb') as file:
                photo_group.append(types.InputMediaPhoto(file.read()))
            data_functions.encrypt_file(file_path)

        elif file_extension == '.pdf':
            document_paths.append(file_path)

    if photo_group:
        await bot.send_media_group(recipient, photo_group)
    
    if document_paths:
        for i, file_path in enumerate(document_paths, 0):
            data_functions.decrypt_file(file_path)
            with open(file_path, 'rb') as file:
                await bot.send_document(recipient, types.InputFile(file), caption=document_names[i])
            data_functions.encrypt_file(file_path)
    
    await bot.send_message(recipient, case_text, parse_mode='Markdown')

async def send_scheduled_message(chat_id, message):
    user_id = chat_id
    user_language = data_functions.get_item_from_table_by_key('user_language', 'users', 'user_id', user_id)
    await bot.send_message(chat_id, message, reply_markup=menus.reply_to_reminder_menu(user_language))

async def schedule_message(chat_id, message, delay=datetime.timedelta(seconds=15)):
    scheduled_time = scheduling.final_scheduled_time(delay, range_minutes=120)
    user_name = data_functions.get_item_from_table_by_key('user_name', 'users', 'user_id', chat_id)
    if user_name == None:
        user_name = 'Bob'
    greeting = scheduling.datetime_to_greeting(scheduled_time, user_name)
    message = greeting + message

    await bot.send_message(chat_id, f'''
Message 
_{message}_ 
will be sent on {scheduled_time.strftime("%Y-%m-%d %H-%M")}
    ''')

    scheduler.add_job(func=send_scheduled_message, name=f'{chat_id}_{datetime.datetime.now().time()}', trigger='date', run_date=scheduled_time, args=[chat_id, message])





#                                    """/-COMMAND HANDLERS""" 

@bot.message_handler(commands=['start'])
async def send_welcome(message):
    user_id = message.chat.id
    user_name = data_functions.get_item_from_table_by_key('user_name', 'users', 'user_id', user_id)
    user_language = data_functions.get_item_from_table_by_key('user_language', 'users', 'user_id', user_id)
    set_user_memory(user_id, ConversationBufferMemory(memory_key="chat_history", return_messages=True))

    if user_name:
        if user_language == 'russian':
            welcome_msg = f"Здравствуйте, {user_name}!"
            menu_msg = "Как могу помочь?"
        elif user_language == 'english':
            welcome_msg = f"Hi, {user_name}!"
            menu_msg = "How can I help?"
        await bot.send_message(user_id, welcome_msg)
        await bot.send_message(user_id, menu_msg, reply_markup=menus.main_menu(user_language))
        set_user_state(user_id, 'awaiting_menu_choice')

    else:
        await bot.send_message(user_id, 'Please select preferred language', reply_markup=menus.set_language_menu())
        set_user_state(message.chat.id, 'awaiting_menu_choice')

@bot.message_handler(commands=['help'])
async def send_help(message):
    help_text = """Быть идеальным ботом непросто. Какой у Вас вопрос? (вам ответит служба поддержки)"""
    await bot.send_message(message.chat.id, help_text)
    set_user_state('requesting_help')

@bot.message_handler(commands=['menu'])
async def show_main_menu(message):
    user_name = data_functions.get_item_from_table_by_key('user_name', 'users', 'user_id', message.chat.id)
    user_language = data_functions.get_item_from_table_by_key('user_language', 'users', 'user_id', user_id)

    if user_language == 'russian':
        msg = f'{user_name}, как я могу Вам помочь?'
    elif user_language == 'english':
        msg = f'{user_name}, how can I help'

    await bot.send_message(message.chat.id, msg, reply_markup=menus.main_menu(user_language))
    set_user_state(message.chat.id, 'awaiting_menu_choice')

@bot.message_handler(commands=['info'])
async def send_info(message):
    user_language = data_functions.get_item_from_table_by_key('user_language', 'users', 'user_id', user_id)

    if user_language == 'russian':
        info = '''
Я помогаю Вам чуточку лучше следить за здоровьем. 
Это open-source проект: https://github.com/mrtroll1/Beta_Health '''
        menu_msg = 'Главное меню'
    elif user_language == 'english':
        info = '''
I help you take care of yourself a bit better.  
This is an open-source project: https://github.com/mrtroll1/Beta_Health '''
        menu_msg = 'Main menu'

    await bot.send_message(message.chat.id, info)
    await bot.send_message(user_id, menu_msg, reply_markup=menus.main_menu(user_language))
    set_user_state(user_id, 'awaiting_menu_choice')
    


    
    

#                                    """STATE HANDLERS"""

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == 'awaiting_menu_choice'
                                            and not message.text.startswith('/'))
async def handle_menu_choice(message):
    user_id = message.chat.id
    user_language = data_functions.get_item_from_table_by_key('user_language', 'users', 'user_id', user_id)

    if user_language == 'russian':
        msg = 'Пожалуйста, выберите вариант из меню.'
    elif user_language == 'english':
        msg = 'Please, choose one of the menu options.'

    await bot.send_message(user_id, msg)

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == 'entering_name'
                                            and not message.text.startswith('/'))
async def handle_name_input(message):
    user_id = message.chat.id
    user_name = message.text

    data_functions.add_user_name(user_id, user_name)

    user_language = data_functions.get_item_from_table_by_key('user_language', 'users', 'user_id', user_id)
    await bot.send_message(user_id, user_language)

    if user_language == 'russian':
        msg = f"Очень приятно, {user_name}! Сейчас я покажу, как всё работает..."
    elif user_language == 'english':
        msg = f"Nice to meet you, {user_name}! Let me explain how everything works..."

    await bot.send_message(user_id, msg)
    await quickstart(message, user_language)

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == 'creating_case'
                                            and not message.text.startswith('/'))
async def handle_message(message):
    user_id = message.chat.id
    user_language = data_functions.get_item_from_table_by_key('user_language', 'users', 'user_id', user_id)
    await conversation_step(message, get_user_memory(message.chat.id), user_language)

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == 'quickstarting'
                                            and not message.text.startswith('/'))
async def handle_message(message):
    user_id = message.chat.id
    user_language = data_functions.get_item_from_table_by_key('user_language', 'users', 'user_id', user_id)
    await conversation_step(message, get_user_memory(message.chat.id), user_language)

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == 'editing_case' 
                                            and not message.text.startswith('/'))
async def edit_case(message):
    user_id = message.chat.id
    user_language = data_functions.get_item_from_table_by_key('user_language', 'users', 'user_id', user_id)
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True) 
    case = get_user_memory(user_id)

    if user_language == 'russian':
        memory.save_context({"input": case}, {"output": "Что бы Вы хотели изменить или добавить?"}) 
        memory.save_context({"input": message.text}, {"output": "Сейчас внесу изменения!"})
        msg = 'Вот обновлённая версия:'
        menu_msg = 'Отправляю врачу?
    elif user_language == 'english':
        memory.save_context({"input": case}, {"output": "What would you like to edit or add?"}) 
        memory.save_context({"input": message.text}, {"output": "I will apply the changes now!"})
        msg = 'Here is the update version:'
        menu_msg = 'Shall I send it to the doctor?'

    await bot.send_message(user_id, msg)
    await bot.send_chat_action(user_id, 'typing')

    case = summarize_into_case(memory)
    set_user_memory(user_id, case)
    case_id = get_user_curr_case(user_id)
    data_functions.alter_table('user_cases', 'case_data', case, 'case_id', case_id)

    await compile_case(case_id, user_id)

    await bot.send_message(user_id, menu_msg, reply_markup=menus.accept_case_menu(user_language))
    set_user_state(user_id, 'awaiting_menu_choice')

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == 'editing_bio'
                                            and not message.text.startswith('/'))
async def edit_bio(message):
    user_id = message.chat.id
    user_language = data_functions.get_item_from_table_by_key('user_language', 'users', 'user_id', user_id)
    data_functions.alter_table('users', 'medical_bio', message.text, 'user_id', user_id)
    
    if user_language == 'russian':
            msg = 'Обновил!'
            menu_msg = 'Главное меню'
    elif user_language == 'english':
        msg = 'Done!'
        menu_msg = 'Main menu'

    await bot.send_message(user_id, msg)
    await bot.send_message(user_id, menu_msg, reply_markup=menus.main_menu(user_language))
    set_user_state(user_id, 'awaiting_menu_choice')

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == 'sending_documents'
                                            and not message.text.startswith('/'))
async def handle_photos(message):
    await save_document(message)
    user_language = data_functions.get_item_from_table_by_key('user_language', 'users', 'user_id', user_id)
    if get_user_state != 'awaiting_menu_choice':
        await bot.send_message(message.chat.id, 'Получил! Хотите отправить больше документов?', reply_markup=menus.more_documents_menu(user_language))
        set_user_state(message.chat.id, 'awaiting_menu_choice')

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == 'quickstart_sending_documents'
                                            and not message.text.startswith('/'))
async def handle_photos(message):
    await save_document(message)
    user_id = message.chat.id
    user_language = data_functions.get_item_from_table_by_key('user_language', 'users', 'user_id', user_id)
    if get_user_state != 'awaiting_menu_choice':

        if user_language == 'russian':
            msg = 'Получил!'
            menu_msg = 'Давайте покажу, что получилось'
        elif user_language == 'english':
            msg = 'Received!'
            menu_msg = 'Let me show you the result'

        await bot.send_message(user_id, msg)
        await bot.send_message(user_id, menu_msg, reply_markup=menus.quickstart_finalize_case_menu(user_language))
        set_user_state(message.chat.id, 'awaiting_menu_choice')


@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == 'setting_reminders'
                                            and not message.text.startswith('/'))
async def set_reminders(message):
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True) 
    reminder_instance = bots.Reminder(bots.llm, bots.reminder_prompt, memory)
    response, reminders = reminder_instance.compose_reminders(message.text)
    user_id = message.chat.id
    user_language = data_functions.get_item_from_table_by_key('user_language', 'users', 'user_id', user_id)

    await bot.send_message(user_id, f'''
*GPT response*: 
{response}
    ''', parse_mode=None)

    await bot.send_message(user_id, f'''
*Parse reminders*: 
{reminders}
    ''')

    if user_language == 'russian':
        plan_data = f'Этот план был создан {datetime.datetime.now().date()} \n{message.text}'
        msg = 'Уведомления были успешно установлены'
        menu_msg = 'Главное меню'
    elif user_language == 'english':
        plan_data = f'This \'to-do\' was created on {datetime.datetime.now().date()} \n{message.text}'
        msg = 'What are your complaints?'
        menu_msg = 'Main menu'

    for reminder_text, delays in reminders.items():
        for delay in delays:
            reminder_text = plan_data + '\n' + reminder_text
            await schedule_message(user_id, reminder_text, delay)

    await bot.send_chat_action(user_id, 'typing')

    data_functions.add_user_plan(user_id, plan_data)
    await bot.send_message(user_id, msg)
    await bot.send_message(user_id, menu_msg, reply_markup=menus.main_menu(user_language))
    set_user_state(user_id, 'awaiting_menu_choice')

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == 'requesting_help'
                                            and not message.text.startswith('/'))
async def set_reminders(message):
    request = message.text
    user_id = message.chat.id
    user_language = data_functions.get_item_from_table_by_key('user_language', 'users', 'user_id', user_id)

    if user_language == 'russian':
        help_msg = f'Пользователь {user_id} обратился в службу поддержки: \n_{message}_'
        msg = 'Отправил службе поддержки'
        menu_msg = 'Главное меню'
    elif user_language == 'english':
        plan_data = f'User {user_id} requested help: \n_{message}_'
        msg = 'Your request was sent'
        menu_msg = 'Main menu'
    
    await bot.send_message(helpservice_telegram_id, help_msg) 
    await bot.send_message(user_id, msg)                       
    await bot.send_message(user_id, menu_msg, reply_markup=menus.main_menu(user_language))
    set_user_state(user_id, 'awaiting_menu_choice')



#                                    """CALLBACK HANDLERS"""

@bot.callback_query_handler(func=lambda call: True)
async def handle_query(call):
    user_id = call.message.chat.id
    user_language = data_functions.get_item_from_table_by_key('user_language', 'users', 'user_id', user_id)

    if call.data == 'new_case':
        await bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
        memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        bio = data_functions.get_item_from_table_by_key('medical_bio', 'users', 'user_id', user_id)
        if bio:
            if user_language == 'russian':
                memory.save_context({'input': f'Общая информация обо мне: {bio}'}, {'output': 'Начинаем. Какие у вас жалобы?'})
            elif user_language == 'english':
                memory.save_context({'input': f'My general bio: {bio}'}, {'output': 'let\'s start. What are your complaints?'})
        else:
            if user_language == 'russian':
                memory.save_context({'input': 'Начнём.'}, {'output': 'Какие у вас жалобы?'})
            elif user_language == 'english':
                memory.save_context({'input': 'Let\'s start.'}, {'output': 'What are your complaints?'})

        set_user_memory(user_id, memory)

        data_functions.increment_value('users', 'num_cases', 'user_id', user_id)
        case_id, num_cases = generate_case_id(user_id)
        set_user_curr_case(user_id, case_id)
        data_functions.add_user_case(case_id, user_id, 'Active')

        if user_language == 'russian':
            msg = 'Какие у вас жалобы?'
        elif user_language == 'english':
            msg = 'What are your complaints?'

        await bot.send_message(user_id, msg)
        set_user_state(user_id, 'creating_case')
        
    elif call.data == 'my_cases':
        await bot.delete_message(chat_id=user_id, message_id=call.message.message_id)

        results = data_functions.get_items_from_table_by_key('case_name', 'user_cases', 'user_id', user_id)
        case_names = [item[0] for item in results]

        results = data_functions.get_items_from_table_by_key('case_id', 'user_cases', 'user_id', user_id)
        case_ids = [item[0] for item in results]
        
        if user_language == 'russian':
            msg = 'Список Ваших проблем:'
        elif user_language == 'english':
            msg = 'List of your complaints:'

        await bot.send_message(user_id, msg, reply_markup=menus.my_cases_menu(case_names, case_ids))
    
    elif call.data == 'my_subscriptions':
        await bot.delete_message(chat_id=user_id, message_id=call.message.message_id)

        if user_language == 'russian':
            msg = 'У Вас нет активных подписок. Чтобы купить, скажите: "Дон-дон"'
            menu_msg = 'Главное меню'
        elif user_language == 'english':
            msg = 'You do not have active subscriptions. To buy one, say "Don-Don"'
            menu_msg = 'Main menu'

        await bot.send_message(user_id, msg)
        await bot.send_message(user_id, menu_msg, reply_markup=menus.main_menu(user_language))
        set_user_state(user_id, 'awaiting_menu_choice')
    
    elif call.data == 'bio':
        await bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
        bio = data_functions.get_item_from_table_by_key('medical_bio', 'users', 'user_id', user_id)
        if bio:
            if user_language == 'russian':
                await bot.send_message(user_id, 'Информация о Вас:')
                await bot.send_message(user_id, bio)
                await bot.send_message(user_id, 'Хотите изменить?', reply_markup=menus.change_bio_menu(user_language))
            elif user_language == 'english':
                await bot.send_message(user_id, 'Your bio:')
                await bot.send_message(user_id, bio)
                await bot.send_message(user_id, 'Want to change it?', reply_markup=menus.change_bio_menu(user_language))

            set_user_state(user_id, 'awaiting_menu_choice')
        else:
            if user_language == 'russian':
                msg = 'Поделитесь полом, возрастом, историей заболеваний или наличием аллергий. Эта информация немного улучшит качество моей работы. Хотите добавить?'
            elif user_language == 'english':
                msg = 'Share your gender, age, medical history or allergies. This information will slighlty improve my performance. Would you like to add it?'

            await bot.send_message(user_id, msg, reply_markup=menus.change_bio_menu(user_language))
            set_user_state(user_id, 'awaiting_menu_choice')

    elif call.data == 'send_case_to_doctor':
        await bot.delete_message(chat_id=user_id, message_id=call.message.message_id)

        if user_language == 'russian':
            msg = 'Чтобы воспользоваться этой функцией, оформите подписку.'
            menu_msg = 'Главное меню'
        elif user_language == 'english':
            msg = 'You need a subscription to share data with doctors.'
            menu_msg = 'Main menu'

        await bot.send_message(user_id, msg)
        await bot.send_message(user_id, menu_msg, reply_markup=menus.main_menu(user_language))
        set_user_state(user_id, 'awaiting_menu_choice')
        # bot.send_message(get_user_doctor(user_id), get_user_memory(user_id))
        # data_functions.alter_table('user_cases', 'case_status', 'shared', 'case_id', case_id)
        # bot.send_message(user_id, 'Отправил врачу! Он скоро с Вами свяжется.')
        # bot.send_message(user_id, 'Лука', reply_markup=menus.main_menu())
        # set_user_state(user_id, 'awaiting_menu_choice')

    elif call.data == 'edit_case':
        await bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
        await bot.send_message(user_id, 'Что бы Вы хотели изменить или добавить?')
        set_user_state(user_id, 'editing_case')
    
    elif call.data == 'edit_bio':
        await bot.delete_message(chat_id=user_id, message_id=call.message.message_id)

        if user_language == 'russian':
            msg = 'Отправьте информацию о Вас одним сообщением'
        elif user_language == 'english':
            msg = 'Send your bio as a single message'

        await bot.send_message(user_id, msg)
        set_user_state(user_id, 'editing_bio')
    
    elif call.data == 'save_bio':
        await bot.delete_message(chat_id=user_id, message_id=call.message.message_id)

        if user_language == 'russian':
            menu_msg = 'Главное меню'
        elif user_language == 'english':
            menu_msg = 'Main menu'

        await bot.send_message(user_id, menu_msg, reply_markup=menus.main_menu(user_language))
        set_user_state(user_id, 'awaiting_menu_choice')
    
    elif call.data == 'add_document':
        await bot.delete_message(chat_id=user_id, message_id=call.message.message_id)

        if user_language == 'russian':
            msg = 'Отправляйте! (Лучше по одному фото или pdf за раз. В общей сложности не больше 10 файлов)'
        elif user_language == 'english':
            msg = 'Send! (Preferrably one photo or pdf at a time. Not more than 10 files in total)'

        await bot.send_message(user_id, msg)
        set_user_state(user_id, 'sending_documents')

    elif call.data == 'quickstart_add_document':
        await bot.delete_message(chat_id=user_id, message_id=call.message.message_id)

        if user_language == 'russian':
            await bot.send_message(user_id, 'Отправляйте!')
        if user_language == 'english':
            await bot.send_message(user_id, 'Send!')

        set_user_state(user_id, 'quickstart_sending_documents')

    elif call.data == 'more_documents':
        await bot.delete_message(chat_id=user_id, message_id=call.message.message_id)

        if user_language == 'russian':
            msg = 'Присылайте документы'
        elif user_language == 'english':
            msg = 'Send documents'

        await bot.send_message(user_id, msg)
        set_user_state(user_id, 'sending_documents')
        
    elif call.data == 'finalize_case':
        await bot.delete_message(chat_id=user_id, message_id=call.message.message_id)

        if user_language == 'russian':
            await bot.send_message(user_id, 'Подождите немного ...')
        elif user_language == 'english':
            await bot.send_message(user_id, 'Give me a second ...')

        await bot.send_chat_action(user_id, 'typing')
        await bot.send_chat_action(user_id, 'upload_document')

        case = summarize_into_case(get_user_memory(user_id))
        set_user_memory(user_id, case)
        case_id = get_user_curr_case(user_id)
        data_functions.alter_table('user_cases', 'case_data', case, 'case_id', case_id)

        await compile_case(case_id, user_id)

        namer_instance = bots.Namer(bots.llm, bots.namer_prompt, ConversationBufferMemory(memory_key="chat_history", return_messages=True))
        case_name = namer_instance.name_case(case)

        if user_language == 'russian':
            await bot.send_message(user_id, f'Я решил назвать эту проблему {case_name}.')
        elif user_language == 'english':
            await bot.send_message(user_id, f'I decided to name your complaint {case_name}.')

        data_functions.alter_table('user_cases', 'case_name', case_name, 'case_id', case_id)

        if user_language == 'russian':
            menu_msg = 'Хотите отправить эти материалы врачу?'
        elif user_language == 'russian':
            menu_msg = 'Do you wish to send that to your doctor'

        await bot.send_message(user_id, menu_msg, reply_markup=menus.accept_case_menu(user_language))
        set_user_state(user_id, 'awaiting_menu_choice')

    elif call.data == 'quickstart_finalize_case':
        await bot.delete_message(chat_id=user_id, message_id=call.message.message_id)

        if user_language == 'russian':
            await bot.send_message(user_id, 'Подождите немного ...')
        elif user_language == 'english':
            await bot.send_message(user_id, 'Give me a second ...')

        await bot.send_chat_action(user_id, 'typing')
        await bot.send_chat_action(user_id, 'upload_document')

        case = summarize_into_case(get_user_memory(user_id))
        set_user_memory(user_id, case)
        case_id = get_user_curr_case(user_id)
        data_functions.alter_table('user_cases', 'case_data', case, 'case_id', case_id)

        await compile_case(case_id, user_id)

        namer_instance = bots.Namer(bots.llm, bots.namer_prompt, ConversationBufferMemory(memory_key="chat_history", return_messages=True))
        case_name = namer_instance.name_case(case)

        if user_language == 'russian':
            await bot.send_message(user_id, f'Я решил назвать эту проблему {case_name} (я не самый талантливый автор названий).')
        elif user_language == 'english':
            await bot.send_message(user_id, f'I decided to name your complaint {case_name} (I am not the greatest namer).')

        data_functions.alter_table('user_cases', 'case_name', case_name, 'case_id', case_id)
        
        if user_language == 'russian':
            msg = 'Теперь Вы умеете работать со мной. Чтобы начать делиться данными с доктором, нужно оформить подписку.'
            menu_msg = 'Главное меню'
        elif user_language == 'english':
            msg = 'Now you know how to work with me. Buy a subscription to start sharing data with a doctor.'
            menu_msg = 'Main menu'

        await bot.send_message(user_id, msg)
        await bot.send_message(user_id, menu_msg, reply_markup=menus.main_menu(user_language))
        set_user_state(user_id, 'awaiting_menu_choice')
    
    elif call.data == 'save_and_not_share':
        await bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
        await bot.send_chat_action(user_id, 'typing')

        case_id = get_user_curr_case(user_id)
        case_name = data_functions.get_item_from_table_by_key('case_name', 'user_cases', 'case_id', case_id)

        if user_language == 'russian':
            msg = f'Проблема {case_name} сохранена.'
            menu_msg = 'Главное меню'
        elif user_language == 'english':
            msg = f'Complaint {case_name} is saved.'
            menu_msg = 'Main menu'

        await bot.send_message(user_id, msg)
        data_functions.alter_table('user_cases', 'case_status', 'saved', 'case_id', case_id)
        await bot.send_message(user_id, menu_msg, reply_markup=menus.main_menu(user_language))
        set_user_state(user_id, 'awaiting_menu_choice')
    
    elif call.data == 'delete_and_not_share':
        await bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
        await bot.send_chat_action(user_id, 'typing')
        case_id = get_user_curr_case(user_id)
        data_functions.delete_row_from_table_by_key('user_cases', 'case_id', case_id)
        data_functions.delete_case(case_id)
        data_functions.decrement_value('users', 'num_cases', 'user_id', user_id)

        if user_language == 'russian':
            msg = 'Данные удалены.'
            menu_msg = 'Главное меню'
        elif user_language == 'english':
            msg = 'Data deleted'
            menu_msg = 'Main menu'

        await bot.send_message(user_id, msg)
        await bot.send_message(user_id, menu_msg, reply_markup=menus.main_menu(user_language))
        set_user_state(user_id, 'awaiting_menu_choice')
    
    elif call.data == 'main_menu':
        await bot.delete_message(user_id, message_id=call.message.message_id)

        if user_language == 'russian':
            menu_msg = 'Как я могу помочь?'
        elif user_language == 'english':
            menu_msg = 'How can I help?'

        await bot.send_message(user_id, menu_msg, reply_markup=menus.main_menu(user_language))
        set_user_state(user_id, 'awaiting_menu_choice')
    
    elif call.data == 'reminders':
        await bot.delete_message(user_id, message_id=call.message.message_id)

        if user_language == 'russian':
            msg = 'Хотите посмотреть имеющиеся напоминания или назначить новые?'
        elif user_language == 'english':
            msg = 'Do you wish to rewise your current reminders or set new ones?'

        await bot.send_message(user_id, msg, reply_markup=menus.reminders_menu(user_language))
        set_user_state(user_id, 'awaiting_menu_choice')
    
    elif call.data == 'my_reminders':
        await bot.delete_message(user_id, message_id=call.message.message_id)
        plans = data_functions.get_items_from_table_by_key('plan_data', 'user_plans', 'user_id', user_id)
        if plans:
            for plan in plans:
                await bot.send_message(user_id, plan[0])
            
            if user_language == 'russian':
                msg = 'Вот то, что Вам необходимо сделать'
            elif user_language == 'english':
                msg = 'This is your current to-do list'

            await bot.send_message(user_id, msg)
        else:

            if user_language == 'russian':
                msg = 'У Вас нет напоминаний.'
            elif user_language == 'english':
                msg = 'You do not have any reminders'

            await bot.send_message(user_id, msg)
    
    elif call.data == 'set_reminders':
        await bot.delete_message(user_id, message_id=call.message.message_id)

        if user_language == 'russian':
            msg = 'Введите рекоммендации врача и даты предстоящих приёмов, и я назначу Вам напоминания.'
        elif user_language == 'english':
            msg = 'Enter doctor recommendations and future appointment dates, and I will set the reminders.'

        await bot.send_message(user_id, msg)
        set_user_state(user_id, 'setting_reminders')
    
    elif call.data == 'reminder_job_done':
        await bot.delete_message(user_id, message_id=call.message.message_id)
        user_name = data_functions.get_item_from_table_by_key('user_name', 'users', 'user_id', user_id)

        if user_language == 'russian':
            msg = f'Молодец, {user_name}'
        elif user_language == 'english':
            msg = f'Good job, {user_name}'

        await bot.send_message(user_id, msg)
    
    elif call.data == 'russian':
        await bot.delete_message(user_id, message_id=call.message.message_id)
        data_functions.add_user_language(user_id, 'russian')
        welcome_msg = "Добро пожаловать! Как я могу к Вам обращаться?"
        set_user_state(user_id, 'entering_name')
        await bot.send_message(user_id, welcome_msg)
    
    elif call.data == 'english':
        await bot.delete_message(user_id, message_id=call.message.message_id)
        data_functions.add_user_language(user_id, 'english')
        welcome_msg = "Welcome! How would you like me to call you?"
        set_user_state(user_id, 'entering_name')
        await bot.send_message(user_id, welcome_msg)

    else:
        await bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
        await bot.send_chat_action(user_id, 'typing')
        await compile_case(call.data, user_id)
        await bot.send_message(user_id, 'Not implemented yet')



        

#                                    """MEDIA HANDLERS"""
@bot.message_handler(content_types=['photo'])
async def handle_photos(message):
    user_id = message.chat.id
    user_state = get_user_state(user_id)

    if user_state == 'sending_documents':
        await save_document(message)
            if get_user_state != 'awaiting_menu_choice':
                
                if user_language == 'russian':
                    msg = 'Получил! Хотите отправить больше документов?'
                elif user_language == 'english':
                    msg = 'Got it! Would you like to attach more documents?'

                await bot.send_message(message.chat.id, msg, reply_markup=menus.more_documents_menu(user_language))
                set_user_state(message.chat.id, 'awaiting_menu_choice')
        
    elif user_state == 'quickstart_sending_documents':
        await save_document(message)
            
            if user_language == 'russian':
                msg = 'Получил! Давайте я покажу, что получилось.'
            elif user_language == 'english':
                msg = 'Got it! Let me show you the result.'

            await bot.send_message(user_id, msg, reply_markup=menus.quickstart_finalize_case_menu(user_language))
            set_user_state(user_id, 'awaiting_menu_choice')

    else:
        if user_language == 'russian':
            msg = 'Кажется, сейчас не самый подходящий момент для этого.'
        elif user_language == 'english':
            msg = 'I wasn\'t expecting to receive this now.'

        await bot.send_message(user_id, msg)

@bot.message_handler(content_types=['document'])
async def handle_document(message):
    user_id = message.chat.id
    user_state = get_user_state(user_id)
    user_language = data_functions.get_item_from_table_by_key('user_language', 'users', 'user_id', user_id)
    
    if user_state == 'sending_documents':
        if message.document.file_name.lower().endswith(('.pdf', '.jpg', '.png', '.jpeg')):
            await save_document(message)
            if get_user_state != 'awaiting_menu_choice':
                
                if user_language == 'russian':
                    msg = 'Получил! Хотите отправить больше документов?'
                elif user_language == 'english':
                    msg = 'Got it! Would you like to attach more documents?'

                await bot.send_message(message.chat.id, msg, reply_markup=menus.more_documents_menu(user_language))
                set_user_state(message.chat.id, 'awaiting_menu_choice')
            
        else:
            if user_language == 'russian':
                msg = 'Увы, но данный формат файлов я не принимаю (только фото и pdf файлы). Хотите прикрепить что-то ещё?'
            elif user_language == 'english':
                msg = 'Unfortunately, this type of documents is not supported (only images or pdf files). Would you like to attach something else?'

            await bot.reply_to(message, msg, reply_markup=menus.more_documents_menu(user_language))
            set_user_state(user_id, 'awaiting_menu_choice')

    elif user_state == 'quickstart_sending_documents':
        if message.document.file_name.lower().endswith(('.pdf', '.jpg', '.png', '.jpeg')):
            await save_document(message)
            
            if user_language == 'russian':
                msg = 'Получил! Давайте я покажу, что получилось.'
            elif user_language == 'english':
                msg = 'Got it! Let me show you the result.'

            await bot.send_message(user_id, msg, reply_markup=menus.quickstart_finalize_case_menu(user_language))
            set_user_state(user_id, 'awaiting_menu_choice')
        else:
            if user_language == 'russian':
                msg = 'Увы, но данный формат файлов я не принимаю (только фото и pdf файлы). Хотите прикрепить что-то ещё?'
            elif user_language == 'english':
                msg = 'Unfortunately, this type of documents is not supported (only images or pdf files). Would you like to attach something else?'

            await bot.reply_to(message, msg, reply_markup=menus.quickstart_add_document_menu(user_language))
            set_user_state(user_id, 'awaiting_menu_choice')

    else:
        if user_language == 'russian':
            msg = 'Кажется, сейчас не самый подходящий момент для этого.'
        elif user_language == 'english':
            msg = 'I wasn\'t expecting to receive this now.'

        await bot.send_message(user_id, msg)





#                                    """REACTIONS HANDLERS"""
@bot.message_reaction_handler()
async def reactions_handler(reaction):
    user_id = reaction.chat.id
    user_language = data_functions.get_item_from_table_by_key('user_language', 'users', 'user_id', user_id)

    if user_language == 'russian':
        msg = f'Ого! Это было клёво ...\nЯ ценю Вашу реакцию на {reaction.message_id}'
    elif user_language == 'english':
        msg = f'Wow! That was cool ...\nI appreciate your reaction to {reaction.message_id}'

    await bot.send_message(user_id, )





async def main():
    scheduler.start()
    await bot.infinity_polling(allowed_updates=['message', 'callback_query', 'message_reaction'])

if __name__ == '__main__':
    asyncio.run(main())