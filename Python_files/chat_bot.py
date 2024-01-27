import os
import time
import asyncio
import bots
import functions
import menus 
import mysql.connector
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
bot = telebot.async_telebot.AsyncTeleBot(telegram_api_token)

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
    
async def conversation_step(message, memory):
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
            await bot.send_message(user_id, 
"""Кажется, я спросил всё, что хотел. Чуть позже у Вас будет возможность что-то изменить или добавить. А сейчас — документы. (Например, сделайте селфи!)""",
            parse_mode='Markdown')
            await bot.send_message(user_id, 'Хотите прикрепить медиа?', reply_markup=menus.quickstart_add_document_menu())
            set_user_state(user_id, 'awaiting_menu_choice')
        else:
            await bot.send_message(user_id, 'Хотите прикрепить медиа?', reply_markup=menus.add_document_menu())
            set_user_state(user_id, 'awaiting_menu_choice')


async def quickstart(message):
    user_id = message.chat.id
    set_user_state(user_id, 'quickstarting')
    await bot.send_chat_action(user_id, 'typing')
    time.sleep(3)
    await bot.send_message(user_id, 'Моя задача — сделать Ваше взаимодействие с доктором проще и удобнее для обеих сторон. Моя главная фишка — система _кейсов_.', parse_mode='Markdown')

    await bot.send_chat_action(user_id, 'typing')
    time.sleep(4)
    await bot.send_message(user_id, 
"""_Кейс_ = Ваши жалобы и симптомы + диагноз и рекоммендации врача. Первую часть кейса составляем мы с Вами вместе. Сценарий такой: \n
Вы обращаетесь ко мне с жалобой; я задаю Вам уточняющие вопросы; Вы подробно на них отвечаете; из переданной информации я составляю текст. \n
Далее, при желании, вы прикрепляете медиафалы. Например, фото симптомов или медицинские справки (если уместно). \n
Когда кейс будет готов, и Вы его утвердите, им можно будет поделиться с Вашим врачом.""", 
    parse_mode='Markdown')

    await bot.send_chat_action(user_id, 'typing')
    time.sleep(4)
    await bot.send_message(user_id, 'Надеюсь, я понятно объяснил. Давайте попробуем! Сейчас я отправлю Вам меню, в котором всего одна кнопка.')
    await bot.send_chat_action(user_id, 'typing')
    time.sleep(2)
    await bot.send_message(user_id, 'Нажимайте!', reply_markup=menus.quickstart_new_case_menu())

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
            file_extension = 'pdf'
            original_file_name = os.path.splitext(doc.file_name)

    elif message.document:
        file_id = message.document.file_id
        file_extension = 'pdf'
        original_file_name = os.path.splitext(message.document.file_name)

    if not file_id:
        print("No supported files found in the message.")
        return

    file_info = await bot.get_file(file_id)
    downloaded_file = await bot.download_file(file_info.file_path)

    case_id = get_user_curr_case(message.chat.id)
    case_specific_path, full_path = functions.save_file_to_server(downloaded_file, message.chat.id, case_id, original_file_name, file_extension)

    functions.alter_table('user_cases', 'case_media_path', case_specific_path, 'case_id', case_id)

async def compile_case(case_id, recipient):
    base_path = '/home/luka/Projects/Beta_Health/User_data/Cases'
    case_path = os.path.join(base_path, str(case_id))
    case_text = functions.get_item_from_table_by_key('case_data', 'user_cases', 'case_id', case_id)

    if not os.path.exists(case_path):
        await bot.send_message(recepeint, 'Данные не найдены')
        return

    photo_group = []
    document_dict = {}
    for filename in os.listdir(case_path):
        if len(photo_group) + len(document_group) >= 10: 
            await bot.send_message(recipient, 'Только первые 10 файлов будут отправлены')
            break

        file_path = os.path.join(case_path, filename)
        functions.decrypt_file(file_path)

        file_extension = os.path.splitext(filename)[1].lower()
        if file_extension in ['.jpg', '.jpeg', '.png']:
            with open(file_path, 'rb') as file:
                photo_group.append(types.InputMediaPhoto(file.read()))
        elif file_extension == '.pdf':
            with open(file_path, 'rb') as file:
                document_dict[types.InputMediaDocument(file.read())] = filename[:-11]

        functions.encrypt_file(file_path)

    if photo_group:
        await bot.send_media_group(recipient, photo_group)
    if document_group:
        for doc in document_dict.keys():
            await bot.send_document(recipient, doc, visible_file_name=document_dict[doc])
    
    await bot.send_message(recipient, case_text, parse_mode='Markdown')




#                                    """/-COMMAND HANDLERS""" 

@bot.message_handler(commands=['start'])
async def send_welcome(message):
    user_id = message.chat.id
    user_name = functions.get_item_from_table_by_key('user_name', 'users', 'user_id', user_id)
    set_user_memory(user_id, ConversationBufferMemory(memory_key="chat_history", return_messages=True))

    if user_name:
        welcome_msg = f"Здравствуйте, {user_name}!"
        await bot.send_message(user_id, welcome_msg)
        await bot.send_message(user_id, "Как могу помочь?", reply_markup=menus.main_menu())
        set_user_state(user_id, 'awaiting_menu_choice')

    else:
        welcome_msg = "Добро пожаловать! Как я могу к Вам обращаться?"
        await bot.send_message(user_id, welcome_msg)
        await bot.register_message_handler(message, handle_name_input)

async def handle_name_input(message):
    user_id = message.chat.id
    user_name = message.text

    functions.add_user_name(user_id, user_name)

    confirmation_msg = f"Очень приятно, {user_name}! Сейчас я расскажу, как всё работает..."
    await bot.send_message(user_id, confirmation_msg)
    quickstart(message)

@bot.message_handler(commands=['help'])
async def send_help(message):
    help_text = """Быть идеальным ботом непросто. Какой у Вас вопрос?"""
    await bot.send_message(message.chat.id, help_text)

@bot.message_handler(commands=['menu'])
async def show_main_menu(message):
    user_name = functions.get_item_from_table_by_key('user_name', 'users', 'user_id', message.chat.id)
    await bot.send_message(message.chat.id, f'{user_name}, как я могу Вам помочь?', reply_markup=menus.main_menu())
    set_user_state(message.chat.id, 'awaiting_menu_choice')

@bot.message_handler(commands=['info'])
async def send_info(message):
    info = 'А чё тут писать-то)'
    await bot.send_message(message.chat.id, info)
    # ... введите /menu, чтобы начать пользоваться

    
    

#                                    """STATE HANDLERS"""

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == 'awaiting_menu_choice'
                                            and not message.text.startswith('/'))
async def handle_menu_choice(message):
    await bot.send_message(message.chat.id, "Пожалуйста, выберите вариант из меню.")

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == 'creating_case'
                                            and not message.text.startswith('/'))
async def handle_message(message):
    await conversation_step(message, get_user_memory(message.chat.id))

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == 'quickstarting'
                                            and not message.text.startswith('/'))
async def handle_message(message):
    await conversation_step(message, get_user_memory(message.chat.id))

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == 'editing_case'
                                            and not message.text.startswith('/'))
async def edit_case(message):
    user_id = message.chat.id
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True) 
    case = get_user_memory(user_id)
    memory.save_context({"input": case}, {"output": "Что бы Вы хотели изменить или добавить?"}) 
    memory.save_context({"input": message.text}, {"output": "Сейчас внесу изменения!"})

    await bot.send_message(user_id, 'Вот обновлённая версия:')
    await bot.send_chat_action(user_id, 'typing')

    case = summarize_into_case(memory)
    set_user_memory(user_id, case)
    case_id = get_user_curr_case(user_id)
    functions.alter_table('user_cases', 'case_data', case, 'case_id', case_id)

    await compile_case(case_id, user_id)
    await bot.send_message(user_id, 'Отправляю врачу?', reply_markup=menus.accept_case_menu())
    set_user_state(user_id, 'awaiting_menu_choice')

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == 'sending_documents'
                                            and not message.text.startswith('/'))
async def handle_photos(message):
    await save_document(message)
    if get_user_state != 'awaiting_menu_choice':
        await bot.send_message(message.chat.id, 'Получил! Хотите отправить больше документов?', reply_markup=menus.more_documents_menu())
        set_user_state(message.chat.id, 'awaiting_menu_choice')

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == 'quickstart_sending_documents'
                                            and not message.text.startswith('/'))
async def handle_photos(message):
    await save_document(message)
    if get_user_state != 'awaiting_menu_choice':
        await bot.send_message(message.chat.id, 'Получил!')
        await bot.send_message(message.chat.id, 'Наш пробный кейс готов! Показать?', reply_markup=menus.quickstart_finalize_case_menu())
        set_user_state(message.chat.id, 'awaiting_menu_choice')




#                                    """CALLBACK HANDLERS"""

@bot.callback_query_handler(func=lambda call: True)
async def handle_query(call):
    user_id = call.message.chat.id

    if call.data == 'new_case':
        await bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
        memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        
        memory.save_context({'input': 'Начнём.'}, {'output': 'Начинаем новый кейс. Какие у вас жалобы?'})
        set_user_memory(user_id, memory)

        functions.increment_value('users', 'num_cases', 'user_id', user_id)
        case_id, num_cases = generate_case_id(user_id)
        set_user_curr_case(user_id, case_id)
        functions.add_user_case(case_id, user_id, 'Активен')

        await bot.send_message(user_id, "Начинаем новый кейс.")
        if get_user_state(user_id) == 'quickstarting':
            await bot.send_message(user_id, 'Какие у Вас жалобы? (подыграйте мне)') 
        else:
            await bot.send_message(user_id, "Какие у вас жалобы?")
            set_user_state(user_id, 'creating_case')
        
    elif call.data == 'my_cases':
        await bot.delete_message(chat_id=user_id, message_id=call.message.message_id)

        results = functions.get_items_from_table_by_key('case_name', 'user_cases', 'user_id', user_id)
        case_names = [item[0] for item in results]

        results = functions.get_items_from_table_by_key('case_id', 'user_cases', 'user_id', user_id)
        case_ids = [item[0] for item in results]
        
        await bot.send_message(user_id, 'Список Ваших кейсов:', reply_markup=menus.my_cases_menu(case_names, case_ids))
    
    elif call.data == 'my_subscriptions':
        await bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
        await bot.send_message(user_id, 'У Вас нет активных подписок. Чтобы купить, скажите: "Дон-дон"')

    elif call.data == 'send_case_to_doctor':
        await bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
        await bot.send_message(user_id, 'Чтобы воспользоваться этой функцией, оформите подписку.')
        # bot.send_message(get_user_doctor(user_id), get_user_memory(user_id))
        # functions.alter_table('user_cases', 'case_status', 'shared', 'case_id', case_id)
        # bot.send_message(user_id, 'Отправил врачу! Он скоро с Вами свяжется.')
        # bot.send_message(user_id, 'Лука', reply_markup=menus.main_menu())
        # set_user_state(user_id, 'awaiting_menu_choice')

    elif call.data == 'edit_case':
        await bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
        await bot.send_message(user_id, 'Что бы Вы хотели изменить или добавить?')
        set_user_state(user_id, 'editing_case')
    
    elif call.data == 'add_document':
        await bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
        await bot.send_message(user_id, 'Отправляйте! (Лучше по одному фото или pdf за раз. В общей сложности не больше 10 файлов)')
        set_user_state(user_id, 'sending_documents')

    elif call.data == 'quickstart_add_document':
        await bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
        await bot.send_message(user_id, 'Отправляйте!')
        set_user_state(user_id, 'quickstart_sending_documents')

    elif call.data == 'more_documents':
        await bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
        await bot.send_message(user_id, 'Присылайте документы')
        set_user_state(user_id, 'sending_documents')
        
    elif call.data == 'finalize_case':
        await bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
        await bot.send_message(user_id, 'Подождите немного, составляю кейс ...')
        await bot.send_chat_action(user_id, 'typing')
        await bot.send_chat_action(user_id, 'upload_document')

        case = summarize_into_case(get_user_memory(user_id))
        set_user_memory(user_id, case)
        case_id = get_user_curr_case(user_id)
        functions.alter_table('user_cases', 'case_data', case, 'case_id', case_id)

        await compile_case(case_id, user_id)

        namer_instance = bots.Namer(bots.llm, bots.namer_prompt, ConversationBufferMemory(memory_key="chat_history", return_messages=True))
        case_name = namer_instance.name_case(case)
        await bot.send_message(user_id, f'Я решил назвать этот кейс {case_name}.')
        functions.alter_table('user_cases', 'case_name', case_name, 'case_id', case_id)
        
        await bot.send_message(user_id, 'Хотите поделиться этим кейсом с врачом?', reply_markup=menus.accept_case_menu())
        set_user_state(user_id, 'awaiting_menu_choice')

    elif call.data == 'quickstart_finalize_case':
        await bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
        await bot.send_message(user_id, 'Подождите немного, составляю кейс ...')
        await bot.send_chat_action(user_id, 'typing')
        await bot.send_chat_action(user_id, 'upload_document')

        case = summarize_into_case(get_user_memory(user_id))
        set_user_memory(user_id, case)
        case_id = get_user_curr_case(user_id)
        functions.alter_table('user_cases', 'case_data', case, 'case_id', case_id)

        await compile_case(case_id, user_id)

        namer_instance = Namer(llm, namer_prompt, ConversationBufferMemory(memory_key="chat_history", return_messages=True))
        case_name = namer_instance.name_case(case)
        await bot.send_message(user_id, f'Вот он наш первый кейс! Я решил назвать его {case_name} (я не самый талантливый автор названий)')
        functions.alter_table('user_cases', 'case_name', case_name, 'case_id', case_id)
        
        await bot.send_message(user_id, 'Теперь Вы умеете создавать кейсы. Чтобы начать делиться ими с доктором, нужно оформить подписку.')
        await bot.send_message(user_id, 'Главное меню', reply_markup=menus.main_menu())
        set_user_state(user_id, 'awaiting_menu_choice')
    
    elif call.data == 'save_and_not_share':
        await bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
        await bot.send_chat_action(user_id, 'typing')

        case_id = get_user_curr_case(user_id)
        case_name = functions.get_item_from_table_by_key('case_name', 'user_cases', 'case_id', case_id)
        await bot.send_message(user_id, f'Кейс {case_name} сохранён.')
        functions.alter_table('user_cases', 'case_status', 'saved', 'case_id', case_id)
        await bot.send_message(user_id, 'Главное меню', reply_markup=menus.main_menu())
        set_user_state(user_id, 'awaiting_menu_choice')
    
    elif call.data == 'delete_and_not_share':
        await bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
        await bot.send_chat_action(user_id, 'typing')
        case_id = get_user_curr_case(user_id)
        functions.delete_row_from_table_by_key('user_cases', 'case_id', case_id)
        functions.delete_case(case_id)
        functions.decrement_value('users', 'num_cases', 'user_id', user_id)
        await bot.send_message(user_id, 'Кейс удалён.')
        await bot.send_message(user_id, 'Главное меню', reply_markup=menus.main_menu())
        set_user_state(user_id, 'awaiting_menu_choice')

    else:
        await bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
        await bot.send_chat_action(user_id, 'typing')

        await compile_case(call.data, user_id)
        await bot.send_message(user_id, 'Тут должно быть какое-то меню, но я его пока не придумал)')



        

#                                    """PHOTO HANDLER"""
@bot.message_handler(content_types=['photo'])
async def handle_photos(message):
    user_id = message.chat.id
    user_state = get_user_state(user_id)

    if user_state == 'sending_documents':
        await save_document(message)
        if get_user_state != 'awaiting_menu_choice':
            await bot.send_message(message.chat.id, 'Получил! Хотите отправить больше документов?', reply_markup=menus.more_documents_menu())
            set_user_state(message.chat.id, 'awaiting_menu_choice')
        
    elif user_state == 'quickstart_sending_documents':
        await save_document(message)
        await bot.send_message(user_id, 'Получил!') 
        await bot.send_message(user_id, 'Наш пробный кейс готов. Показать?', reply_markup=menus.quickstart_finalize_case_menu())
        set_user_state(user_id, 'awaiting_menu_choice')

    else:
        await bot.send_message(user_id, "Кажется, сейчас не самый подходящий момент для этого.")

@bot.message_handler(content_types=['document'])
async def handle_document(message):
    user_id = message.chat.id
    user_state = get_user_state(user_id)
    
    if user_state == 'sending_documents':
        if message.document.file_name.lower().endswith('.pdf'):
            await save_document(message)
            if get_user_state != 'awaiting_menu_choice':
                await bot.send_message(message.chat.id, 'Получил! Хотите отправить больше документов?', reply_markup=menus.more_documents_menu())
                set_user_state(message.chat.id, 'awaiting_menu_choice')
            
        else:
            await bot.reply_to(message, "Увы, но данный формат файлов я не принимаю. Хотите прикрепить что-то ещё?", reply_markup=menus.more_documents_menu())
            set_user_state(user_id, 'awaiting_menu_choice')

    elif user_state == 'quickstart_sending_documents':
        if message.document.file_name.lower().endswith('.pdf'):
            await save_document(message)
            await bot.send_message(user_id, 'Получил!', reply_markup=menus.quickstart_finalize_case_menu())
            await bot.send_message(user_id, 'Наш пробный кейс готов. Показать?', reply_markup=menus.quickstart_finalize_case_menu())
            set_user_state(user_id, 'awaiting_menu_choice')
        else:
            await bot.reply_to(message, "Увы, но данный формат файлов я не принимаю. Хотите прикрепить что-то ещё?", reply_markup=menus.quickstart_add_document_menu())
            set_user_state(user_id, 'awaiting_menu_choice')

    else:
        await bot.send_message(user_id, "Кажется, сейчас не самый подходящий момент для этого.")


async def main():
    await bot.infinity_polling()

if __name__ == '__main__':
    asyncio.run(main())