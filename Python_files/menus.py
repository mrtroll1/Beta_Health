import telebot
from telebot import types

def main_menu():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row_width = 1

    button_1 = types.InlineKeyboardButton("📝 Новая проблема", callback_data='new_case')
    button_2 = types.InlineKeyboardButton("🗃 Активные проблемы", callback_data='my_cases')
    игеещт_3 = types.InlineKeyboardButton("🔔 Напоминания", callback_data='reminders')
    button_4 = types.InlineKeyboardButton("🔐 Мои подписки", callback_data='my_subscriptions')
    button_5 = types.InlineKeyboardButton("👤 Обо мне", callback_data='bio')

    keyboard.add(button_1, button_2, button_3, button_4, button_5)

    return keyboard

def my_cases_menu(case_names, case_ids):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row_width = 1

    for i in range(len(case_names)):
        button = types.InlineKeyboardButton(f'🗒 {case_names[i]}', callback_data=case_ids[i])
        keyboard.add(button)
    
    button = types.InlineKeyboardButton("<< Назад", callback_data='main_menu')
    keyboard.add(button)

    return keyboard

def change_bio_menu():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row_width = 1

    button_1 = types.InlineKeyboardButton("Да", callback_data='edit_bio')
    button_2 = types.InlineKeyboardButton("Нет", callback_data='save_bio')

    keyboard.add(button_1, button_2)

    return keyboard

def accept_case_menu():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row_width = 1

    button_1 = types.InlineKeyboardButton("Да, отправляй!", callback_data='send_case_to_doctor')
    button_2 = types.InlineKeyboardButton("Хочу изменить", callback_data='edit_case')
    button_3 = types.InlineKeyboardButton("Сохрани, но не отправляй врачу", callback_data='save_and_not_share')
    button_4 = types.InlineKeyboardButton("Не сохраняй и не отправляй врачу", callback_data='delete_and_not_share')

    keyboard.add(button_1, button_2, button_3, button_4)

    return keyboard

def add_document_menu():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row_width = 1

    button_1 = types.InlineKeyboardButton("Да", callback_data='add_document')
    button_2 = types.InlineKeyboardButton("Нет", callback_data='finalize_case')

    keyboard.add(button_1, button_2)

    return keyboard

def more_documents_menu():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row_width = 1

    button_1 = types.InlineKeyboardButton("Да", callback_data='more_documents')
    button_2 = types.InlineKeyboardButton("Нет", callback_data='finalize_case')

    keyboard.add(button_1, button_2)

    return keyboard

def reminders_menu():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row_width = 1

    button_1 = types.InlineKeyboardButton("Посмотреть напоминания", callback_data='my_reminders')
    button_2 = types.InlineKeyboardButton("Назначить новые напоминания", callback_data='set_reminders')
    button = types.InlineKeyboardButton("<< Назад", callback_data='main_menu')

    keyboard.add(button_1, button_2)

    return keyboard

def quickstart_new_case_menu():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row_width = 1

    button_1 = types.InlineKeyboardButton("📝 Начать новую проблему", callback_data='new_case')

    keyboard.add(button_1)

    return keyboard

def quickstart_add_document_menu():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row_width = 1

    button_1 = types.InlineKeyboardButton("Хочу!", callback_data='quickstart_add_document')

    keyboard.add(button_1)

    return keyboard

def quickstart_finalize_case_menu():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row_width = 1

    button_1 = types.InlineKeyboardButton("Давай!", callback_data='quickstart_finalize_case')

    keyboard.add(button_1)

    return keyboard