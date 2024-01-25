import telebot
from telebot import types

def main_menu():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row_width = 1

    button_1 = types.InlineKeyboardButton("Новый кейс", callback_data='new_case')
    button_2 = types.InlineKeyboardButton("Мои кейсы", callback_data='my_cases')
    button_3 = types.InlineKeyboardButton("Мои подписки", callback_data='my_subscriptions')

    keyboard.add(button_1, button_2, button_3)

    return keyboard

def my_cases_menu(case_names, case_ids):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row_width = 1

    for i in range(len(case_names)):
        button = types.InlineKeyboardButton(case_names[i], callback_data=case_ids[i])
        keyboard.add(button)

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

def quickstart_new_case_menu():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row_width = 1

    button_1 = types.InlineKeyboardButton("Начать новый кейс", callback_data='new_case')

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