import os
import mysql.connector
import telebot
import time
from telebot import types
from bots import ChatBot, Summarizer, Namer
import functions
import menus 
from langchain.prompts import ChatPromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import MessagesPlaceholder
from langchain.schema import SystemMessage
from langchain.prompts import HumanMessagePromptTemplate

openai_api_key = os.environ.get('OPENAI_API_KEY')
telegram_api_token = os.environ.get('TELEGRAM_API_TOKEN')
# webhook_url = os.environ.get('WEBHOOK_URL')

bot = telebot.TeleBot(telegram_api_token)

llm = ChatOpenAI(openai_api_key=openai_api_key, model_name='gpt-4')  

prompt = ChatPromptTemplate.from_messages(
    [
        SystemMessage(
            content="""Ты - виртаульный ассистент врача. Твоя задача принять жалобу или вопрос от пациента и вступить с 
            ним в диалог, задавая вопросы о его проблеме. Получи следующую информацию о симптомах: начало, локализация, продолжительность, характер, облегчающие/усугубляющие факторы, 
            временная закономерность, интенсивность, история похожих болезней/симптомов. Задай много вопросов, чтобы собрать много деталей. Каждый вопрос должен быть отдельным сообщением. 
            Затем, твоя задача указать возможные причины для состояния пациента. Это сообщение должно оканчиваться двумя символами ##. 
            Также, можешь посоветовать простые методы лечения, у которых известный уровень доказанности. Это сообщение тоже должно оканчиваться двумя символами ##.
            Обращайся к пациенту на Вы. Если какой-то вопрос или сообщение от пациента не соотвествует
            тематике здравоохранения, то напомни ему об этом. Старайся писать не длинные сообщения. """
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
            Твоя задача, сохраня все фактические детали, отформатировать переданную пациентом информацию
            о его состоянии в текст. Твой ответ доленж иметь две секции: **жалобы** и **предворительные рекоммендации**. Не используй в тексте слова "пациент" или "у вас". 
            Например, вместо "Пациент жалуется на трёхдневную боль в горле" или
            "У вас три дня болит горло", напиши "Три дня боль в горле." 
            Не указывай возможные причины. Не задавай вопросов.
            Используй только  симптомы, содержащиеся в ответах пациента. """
        ),  
        MessagesPlaceholder(
            variable_name="chat_history"
        ),  
        HumanMessagePromptTemplate.from_template(
            "{human_input}"
        ),  
    ]
)

namer_prompt = ChatPromptTemplate.from_messages(
    [
        SystemMessage(
            content="""Тебе на вход даётся кейс - набор жалоб и симптомов пациента. 
            Твоя задача придумать ему короткое название. Название не должно быть дольше трёх слов. 
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
    
def conversation_step(message, memory):
    user_id = message.chat.id
    bot_instance = ChatBot(llm, prompt, memory)

    bot.send_chat_action(user_id, 'typing')
    response = bot_instance.process_message(message.text)
    response = chatgpt_to_telegram_markdown(response)
    bot.send_message(user_id, response, parse_mode='Markdown')

    set_user_memory(user_id, memory)

    symbol_combination = '##'
    if symbol_combination in response:
        if get_user_state(user_id) == 'quickstarting':
            bot.send_chat_action(user_id, 'typing')
            bot.send_message(user_id, 
"""Кажется, я спросил всё, что хотел. Чуть позже у Вас будет возможность что-то изменить или добавить. А сейчас — документы. (Например, сделайте селфи!)""",
            parse_mode='Markdown')
            bot.send_message(user_id, 'Хотите прикрепить медиа?', reply_markup=menus.quickstart_add_document_menu())
            set_user_state(user_id, 'awaiting_menu_choice')
        else:
            bot.send_message(user_id, 'Хотите прикрепить медиа?', reply_markup=menus.add_document_menu())
            set_user_state(user_id, 'awaiting_menu_choice')


def quickstart(message):
    user_id = message.chat.id
    set_user_state(user_id, 'quickstarting')
    bot.send_chat_action(user_id, 'typing')
    time.sleep(3)
    bot.send_message(user_id, 'Моя задача — сделать Ваше взаимодействие с доктором проще и удобнее для обеих сторон. Моя главная фишка — система _кейсов_.', parse_mode='Markdown')

    bot.send_chat_action(user_id, 'typing')
    time.sleep(4)
    bot.send_message(user_id, 
"""_Кейс_ = Ваши жалобы и симптомы + диагноз и рекоммендации врача. Первую часть кейса составляем мы с Вами вместе. Сценарий такой: \n
Вы обращаетесь ко мне с жалобой; я задаю Вам уточняющие вопросы; Вы подробно на них отвечаете; из переданной информации я составляю текст. \n
Далее, при желании, вы прикрепляете медиафалы. Например, фото симптомов или медицинские справки (если уместно). \n
Когда кейс будет готов, и Вы его утвердите, им можно будет поделиться с Вашим врачом.""", 
    parse_mode='Markdown')

    bot.send_chat_action(user_id, 'typing')
    time.sleep(4)
    bot.send_message(user_id, 'Надеюсь, я понятно объяснил. Давайте попробуем! Сейчас я отправлю Вам меню, в котором всего одна кнопка.')
    bot.send_chat_action(user_id, 'typing')
    time.sleep(2)
    bot.send_message(user_id, 'Нажимайте!', reply_markup=menus.quickstart_new_case_menu())

def summarize_into_case(memory): 
    summarizer_instance = Summarizer(llm, summarizer_prompt, memory)
    summary = summarizer_instance.summarize(memory)
    return chatgpt_to_telegram_markdown(summary)

def save_document(message):
    file_id = None
    file_extension = None

    if isinstance(message.photo, list) and message.photo:
        largest_photo = message.photo[-1]
        file_id = largest_photo.file_id
        file_extension = 'jpg' 

    elif isinstance(message.document, list):
        for doc in message.document:
            file_id = doc.file_id
            file_extension = 'pdf'
    elif message.document:
        file_id = message.document.file_id
        file_extension = 'pdf'

    if not file_id:
        print("No supported files found in the message.")
        return

    file_info = bot.get_file(file_id)
    downloaded_file = bot.download_file(file_info.file_path)

    case_id = get_user_curr_case(message.chat.id)
    case_specific_path, full_path = functions.save_file_to_server(downloaded_file, message.chat.id, case_id, file_extension)

    functions.alter_table('user_cases', 'case_media_path', case_specific_path, 'case_id', case_id)

def compile_case(case_id, recepient):
    base_path = '/home/luka/Projects/Beta_Health/User_data/Cases'
    case_path = os.path.join(base_path, str(case_id))
    case_text = functions.get_item_from_table_by_key('case_data', 'user_cases', 'case_id', case_id)

    if not os.path.exists(case_path):
        print(f"No directory found for case ID {case_id}")
        return

    photo_group = []
    document_group = []
    for filename in os.listdir(case_path):
        if len(photo_group) + len(document_group) >= 10: 
            bot.send_message(recepient, 'Только первые 10 файлов будут отправлены')
            break

        file_path = os.path.join(case_path, filename)
        functions.decrypt_file(file_path)

        file_extension = os.path.splitext(filename)[1].lower()
        if file_extension in ['.jpg', '.jpeg', '.png']:
            with open(file_path, 'rb') as file:
                photo_group.append(types.InputMediaPhoto(file.read()))
        elif file_extension == '.pdf':
            with open(file_path, 'rb') as file:
                document_group.append(types.InputMediaDocument(file.read()))

        functions.encrypt_file(file_path)

    if photo_group:
        bot.send_media_group(recepient, photo_group)
    if document_group:
        bot.send_media_group(recepient, document_group)
    
    bot.send_message(recepient, case_text, parse_mode='Markdown')




#                                    """/-COMMAND HANDLERS""" 

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.chat.id
    user_name = functions.get_item_from_table_by_key('user_name', 'users', 'user_id', user_id)
    set_user_memory(user_id, ConversationBufferMemory(memory_key="chat_history", return_messages=True))
    
    if user_name:
        welcome_msg = f"Здравствуйте, {user_name}!"
        bot.send_message(user_id, welcome_msg)
        bot.send_message(user_id, "Как могу помочь?", reply_markup=menus.main_menu())
        set_user_state(user_id, 'awaiting_menu_choice')
        
    else:
        welcome_msg = "Добро пожаловать! Как я могу к Вам обращаться?"
        bot.send_message(user_id, welcome_msg)
        bot.register_next_step_handler(message, handle_name_input)

def handle_name_input(message):
    user_id = message.chat.id
    user_name = message.text    

    functions.add_user_name(user_id, user_name)  

    confirmation_msg = f"Очень приятно, {user_name}! Сейчас я расскажу, как всё работает..."
    bot.send_message(user_id, confirmation_msg)
    quickstart(message)

@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = """Напоминаю, что подробно о работе бота можно почитать по команде /info. 
    Какой у Вас вопрос?"""
    bot.send_message(message.chat.id, help_text)

@bot.message_handler(commands=['menu'])
def show_main_menu(message):
    user_name = functions.get_item_from_table_by_key('user_name', 'users', 'user_id', message.chat.id)
    bot.send_message(message.chat.id, f'{user_name}, как я могу Вам помочь?', reply_markup=menus.main_menu())
    set_user_state(message.chat.id, 'awaiting_menu_choice')

@bot.message_handler(commands=['info'])
def send_info(message):
    info = 'Вот как всё работает ...'
    bot.send_message(message.chat.id, info)
    # ... введите /menu, чтобы начать пользоваться

    
    

#                                    """STATE HANDLERS"""

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == 'awaiting_menu_choice'
                                            and not message.text.startswith('/'))
def handle_menu_choice(message):
    bot.send_message(message.chat.id, "Пожалуйста, выберите вариант из меню.")

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == 'creating_case'
                                            and not message.text.startswith('/'))
def handle_message(message):
    conversation_step(message, get_user_memory(message.chat.id))

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == 'quickstarting'
                                            and not message.text.startswith('/'))
def handle_message(message):
    conversation_step(message, get_user_memory(message.chat.id))

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == 'editing_case'
                                            and not message.text.startswith('/'))
def edit_case(message):
    user_id = message.chat.id
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True) 
    case = get_user_memory(user_id)
    memory.save_context({"input": case}, {"output": "Что бы Вы хотели изменить или добавить?"}) 
    memory.save_context({"input": message.text}, {"output": "Сейчас внесу изменения!"})

    bot.send_message(user_id, 'Вот обновлённая версия:')
    bot.send_chat_action(user_id, 'typing')

    case = summarize_into_case(memory)
    set_user_memory(user_id, case)
    case_id = get_user_curr_case(user_id)
    functions.alter_table('user_cases', 'case_data', case, 'case_id', case_id)

    compile_case(case_id, user_id)
    bot.send_message(user_id, 'Отправляю врачу?', reply_markup=menus.accept_case_menu())
    set_user_state(user_id, 'awaiting_menu_choice')

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == 'sending_documents'
                                            and not message.text.startswith('/'))
def handle_photos(message):
    save_document(message)
    if get_user_state != 'awaiting_menu_choice':
        bot.send_message(message.chat.id, 'Получил! Хотите отправить больше документов?', reply_markup=menus.more_documents_menu())
        set_user_state(message.chat.id, 'awaiting_menu_choice')

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == 'quickstart_sending_documents'
                                            and not message.text.startswith('/'))
def handle_photos(message):
    save_document(message)
    if get_user_state != 'awaiting_menu_choice':
        bot.send_message(message.chat.id, 'Получил!')
        bot.send_message(message.chat.id, 'Наш пробный кейс готов! Показать?', reply_markup=menus.quickstart_finalize_case_menu())
        set_user_state(message.chat.id, 'awaiting_menu_choice')




#                                    """CALLBACK HANDLERS"""

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    user_id = call.message.chat.id

    if call.data == 'new_case':
        bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
        memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        
        memory.save_context({'input': 'Начнём.'}, {'output': 'Начинаем новый кейс. Какие у вас жалобы?'})
        set_user_memory(user_id, memory)

        functions.increment_value('users', 'num_cases', 'user_id', user_id)
        case_id, num_cases = generate_case_id(user_id)
        set_user_curr_case(user_id, case_id)
        functions.add_user_case(case_id, user_id, 'started')

        bot.send_message(user_id, "Начинаем новый кейс.")
        if get_user_state(user_id) == 'quickstarting':
            bot.send_message(user_id, 'Какие у Вас жалобы? (подыграйте мне)') 
        else:
            bot.send_message(user_id, "Какие у вас жалобы?")
            set_user_state(user_id, 'creating_case')
        
    elif call.data == 'my_cases':
        bot.delete_message(chat_id=user_id, message_id=call.message.message_id)

        results = functions.get_items_from_table_by_key('case_name', 'user_cases', 'user_id', user_id)
        case_names = [item[0] for item in results]

        results = functions.get_items_from_table_by_key('case_id', 'user_cases', 'user_id', user_id)
        case_ids = [item[0] for item in results]
        
        bot.send_message(user_id, 'Список Ваших кейсов:', reply_markup=menus.my_cases_menu(case_names, case_ids))
    
    elif call.data == 'my_subscriptions':
        bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
        bot.send_message(user_id, 'У Вас нет активных подписок.')

    elif call.data == 'send_case_to_doctor':
        bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
        bot.send_message(user_id, 'Чтобы воспользоваться этой функцией, оформите подписку.')
        # bot.send_message(get_user_doctor(user_id), get_user_memory(user_id))
        # functions.alter_table('user_cases', 'case_status', 'shared', 'case_id', case_id)
        # bot.send_message(user_id, 'Отправил врачу! Он скоро с Вами свяжется.')
        # bot.send_message(user_id, 'Лука', reply_markup=menus.main_menu())
        # set_user_state(user_id, 'awaiting_menu_choice')

    elif call.data == 'edit_case':
        bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
        bot.send_message(user_id, 'Что бы Вы хотели изменить или добавить?')
        set_user_state(user_id, 'editing_case')
    
    elif call.data == 'add_document':
        bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
        bot.send_message(user_id, 'Отправляйте! (Лучше по одному фото или pdf за раз. В общей сложности не больше 10 файлов)')
        set_user_state(user_id, 'sending_documents')

    elif call.data == 'quickstart_add_document':
        bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
        bot.send_message(user_id, 'Отправляйте!')
        set_user_state(user_id, 'quickstart_sending_documents')

    elif call.data == 'more_documents':
        bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
        bot.send_message(user_id, 'Присылайте документы')
        set_user_state(user_id, 'sending_documents')
        
    elif call.data == 'finalize_case':
        bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
        bot.send_message(user_id, 'Подождите немного, составляю кейс ...')
        bot.send_chat_action(user_id, 'typing')
        bot.send_chat_action(user_id, 'upload_document')

        case = summarize_into_case(get_user_memory(user_id))
        set_user_memory(user_id, case)
        case_id = get_user_curr_case(user_id)
        functions.alter_table('user_cases', 'case_data', case, 'case_id', case_id)

        compile_case(case_id, user_id)

        namer_instance = Namer(llm, namer_prompt, ConversationBufferMemory(memory_key="chat_history", return_messages=True))
        case_name = namer_instance.name_case(case)
        bot.send_message(user_id, f'Я решил назвать этот кейс {case_name}.')
        functions.alter_table('user_cases', 'case_name', case_name, 'case_id', case_id)
        
        bot.send_message(user_id, 'Хотите поделиться этим кейсом с врачом?', reply_markup=menus.accept_case_menu())
        set_user_state(user_id, 'awaiting_menu_choice')

    elif call.data == 'quickstart_finalize_case':
        bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
        bot.send_message(user_id, 'Подождите немного, составляю кейс ...')
        bot.send_chat_action(user_id, 'typing')
        bot.send_chat_action(user_id, 'upload_document')

        case = summarize_into_case(get_user_memory(user_id))
        set_user_memory(user_id, case)
        case_id = get_user_curr_case(user_id)
        functions.alter_table('user_cases', 'case_data', case, 'case_id', case_id)

        compile_case(case_id, user_id)

        namer_instance = Namer(llm, namer_prompt, ConversationBufferMemory(memory_key="chat_history", return_messages=True))
        case_name = namer_instance.name_case(case)
        bot.send_message(user_id, f'Вот он наш первый кейс! Я решил назвать его {case_name} (я не самый талантливый автор названий)')
        functions.alter_table('user_cases', 'case_name', case_name, 'case_id', case_id)
        
        bot.send_message(user_id, 'Теперь Вы умеете создавать кейсы. Чтобы начать делиться ими с доктором, нужно оформить подписку.')
        bot.send_message(user_id, 'Главное меню', reply_markup=menus.main_menu())
        set_user_state(user_id, 'awaiting_menu_choice')
    
    elif call.data == 'save_and_not_share':
        bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
        bot.send_chat_action(user_id, 'typing')

        case_id = get_user_curr_case(user_id)
        case_name = functions.get_item_from_table_by_key('case_name', 'user_cases', 'case_id', case_id)
        bot.send_message(user_id, f'Кейс {case_name} сохранён.')
        functions.alter_table('user_cases', 'case_status', 'saved', 'case_id', case_id)
        bot.send_message(user_id, 'Главное меню', reply_markup=menus.main_menu())
        set_user_state(user_id, 'awaiting_menu_choice')
    
    elif call.data == 'delete_and_not_share':
        bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
        bot.send_chat_action(user_id, 'typing')
        case_id = get_user_curr_case(user_id)
        functions.delete_row_from_table_by_key('user_cases', 'case_id', case_id)
        functions.delete_case(case_id)
        functions.decrement_value('users', 'num_cases', 'user_id', user_id)
        bot.send_message(user_id, 'Кейс удалён.')
        bot.send_message(user_id, 'Главное меню', reply_markup=menus.main_menu())
        set_user_state(user_id, 'awaiting_menu_choice')

    else:
        bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
        bot.send_chat_action(user_id, 'typing')

        compile_case(call.data, user_id)
        bot.send_message(user_id, 'Тут должно быть какое-то меню, но я его пока не придумал)')



        

#                                    """PHOTO HANDLER"""
@bot.message_handler(content_types=['photo'])
def handle_photos(message):
    user_id = message.chat.id
    user_state = get_user_state(user_id)

    if user_state == 'sending_documents':
        save_document(message)
        if get_user_state != 'awaiting_menu_choice':
            bot.send_message(message.chat.id, 'Получил! Хотите отправить больше документов?', reply_markup=menus.more_documents_menu())
            set_user_state(message.chat.id, 'awaiting_menu_choice')
        
    elif user_state == 'quickstart_sending_documents':
        save_document(message)
        bot.send_message(user_id, 'Получил!') 
        bot.send_message(user_id, 'Наш пробный кейс готов. Показать?', reply_markup=menus.quickstart_finalize_case_menu())
        set_user_state(user_id, 'awaiting_menu_choice')

    else:
        bot.send_message(user_id, "Кажется, сейчас не самый подходящий момент для этого.")

@bot.message_handler(content_types=['document'])
def handle_document(message):
    user_id = message.chat.id
    user_state = get_user_state(user_id)
    
    if user_state == 'sending_documents':
        if message.document.file_name.lower().endswith('.pdf'):
            save_document(message)
            if get_user_state != 'awaiting_menu_choice':
                bot.send_message(message.chat.id, 'Получил! Хотите отправить больше документов?', reply_markup=menus.more_documents_menu())
                set_user_state(message.chat.id, 'awaiting_menu_choice')
            
        else:
            bot.reply_to(message, "Увы, но данный формат файлов я не принимаю. Хотите прикрепить что-то ещё?", reply_markup=menus.more_documents_menu())
            set_user_state(user_id, 'awaiting_menu_choice')

    elif user_state == 'quickstart_sending_documents':
        if message.document.file_name.lower().endswith('.pdf'):
            save_document(message)
            bot.send_message(user_id, 'Получил!', reply_markup=menus.quickstart_finalize_case_menu())
            bot.send_message(user_id, 'Наш пробный кейс готов. Показать?', reply_markup=menus.quickstart_finalize_case_menu())
            set_user_state(user_id, 'awaiting_menu_choice')
        else:
            bot.reply_to(message, "Увы, но данный формат файлов я не принимаю. Хотите прикрепить что-то ещё?", reply_markup=menus.quickstart_add_document_menu())
            set_user_state(user_id, 'awaiting_menu_choice')

    else:
        bot.send_message(user_id, "Кажется, сейчас не самый подходящий момент для этого.")


bot.infinity_polling()