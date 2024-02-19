# This file contains InlineKeyabord menus 

import telebot
from telebot import types

def main_menu(language):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row_width = 1

    if language == 'russian':
        button_1 = types.InlineKeyboardButton("📝 Новая жалоба", callback_data='new_case')
        button_2 = types.InlineKeyboardButton("🗃 Активные жалобы", callback_data='my_cases')
        button_3 = types.InlineKeyboardButton("🔔 Напоминания", callback_data='reminders')
        button_4 = types.InlineKeyboardButton("🔐 Мои подписки", callback_data='my_subscriptions')
        button_5 = types.InlineKeyboardButton("👤 Обо мне", callback_data='bio')
    elif language == 'english':
        button_1 = types.InlineKeyboardButton("📝 New complaint", callback_data='new_case')
        button_2 = types.InlineKeyboardButton("🗃 Active complaints", callback_data='my_cases')
        button_3 = types.InlineKeyboardButton("🔔 Reminders", callback_data='reminders')
        button_4 = types.InlineKeyboardButton("🔐 Subscriptions", callback_data='my_subscriptions')
        button_5 = types.InlineKeyboardButton("👤 Bio", callback_data='bio')

    keyboard.add(button_1, button_2, button_3, button_4, button_5)

    return keyboard

def go_back_menu(callback_data):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row_width = 1

    button_1 = types.InlineKeyboardButton("<<", callback_data=callback_data)

    keyboard.add(button_1)

    return keyboard

def set_language_menu():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row_width = 1

    button_1 = types.InlineKeyboardButton("Русский", callback_data='russian')
    button_2 = types.InlineKeyboardButton("English", callback_data='english')

    keyboard.add(button_1, button_2)

    return keyboard

def my_cases_menu(case_names, case_ids):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row_width = 1

    for i in range(len(case_names)):
        button = types.InlineKeyboardButton(f'🗒 {case_names[i]}', callback_data=case_ids[i])
        keyboard.add(button)
    
    button = types.InlineKeyboardButton("<<", callback_data='main_menu')
    keyboard.add(button)

    return keyboard

def change_bio_menu(language):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row_width = 1

    if language == 'russian':
        button_1 = types.InlineKeyboardButton("Да", callback_data='edit_bio')
        button_2 = types.InlineKeyboardButton("Нет", callback_data='save_bio')
    elif language == 'english':
        button_1 = types.InlineKeyboardButton("Yes", callback_data='edit_bio')
        button_2 = types.InlineKeyboardButton("No", callback_data='save_bio')

    keyboard.add(button_1, button_2)

    return keyboard

def accept_case_menu(language):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row_width = 1

    if language == 'russian':
        button_1 = types.InlineKeyboardButton("Отправить врачу", callback_data='send_case_to_doctor')
        button_2 = types.InlineKeyboardButton("Хочу изменить", callback_data='edit_case')
        button_3 = types.InlineKeyboardButton("Сохрани", callback_data='save_and_not_share')
        button_4 = types.InlineKeyboardButton("Удали", callback_data='delete_and_not_share')
    elif language == 'english':
        button_1 = types.InlineKeyboardButton("Send to doctor", callback_data='send_case_to_doctor')
        button_2 = types.InlineKeyboardButton("I want to make changes", callback_data='edit_case')
        button_3 = types.InlineKeyboardButton("Save", callback_data='save_and_not_share')
        button_4 = types.InlineKeyboardButton("Delete", callback_data='delete_and_not_share')

    keyboard.add(button_1, button_2, button_3, button_4)

    return keyboard

def add_document_menu(language):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row_width = 1

    if language == 'russian':
        button_1 = types.InlineKeyboardButton("Да", callback_data='add_document')
        button_2 = types.InlineKeyboardButton("Нет", callback_data='finalize_case')
    elif language == 'english':
        button_1 = types.InlineKeyboardButton("Yes", callback_data='add_document')
        button_2 = types.InlineKeyboardButton("No", callback_data='finalize_case')

    keyboard.add(button_1, button_2)

    return keyboard

def more_documents_menu(language):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row_width = 1

    if language == 'russian':
        button_1 = types.InlineKeyboardButton("Да", callback_data='more_documents')
        button_2 = types.InlineKeyboardButton("Нет", callback_data='finalize_case')
    elif language == 'english':
        button_1 = types.InlineKeyboardButton("Yes", callback_data='more_documents')
        button_2 = types.InlineKeyboardButton("No", callback_data='finalize_case')

    keyboard.add(button_1, button_2)

    return keyboard

def reminders_menu(language):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row_width = 1

    if language == 'russian':
        button_1 = types.InlineKeyboardButton("Посмотреть напоминания", callback_data='my_reminders')
        button_2 = types.InlineKeyboardButton("Назначить новые напоминания", callback_data='set_reminders')
        button_3 = types.InlineKeyboardButton("<<", callback_data='main_menu')
    elif language == 'english':
        button_1 = types.InlineKeyboardButton("See existing reminders", callback_data='my_reminders')
        button_2 = types.InlineKeyboardButton("Set new reminders", callback_data='set_reminders')
        button_3 = types.InlineKeyboardButton("<<", callback_data='main_menu')

    keyboard.add(button_1, button_2, button_3)

    return keyboard

def reply_to_reminder_menu(language):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row_width = 1

    if language == 'russian':
        button_1 = types.InlineKeyboardButton("Уже сделал", callback_data='reminder_job_done')
        button_1 = types.InlineKeyboardButton("Спасибо, что напомнил", callback_data='reminder_job_not_done')
    elif language == 'english':
        button_1 = types.InlineKeyboardButton("I have already done it", callback_data='reminder_job_done')
        button_1 = types.InlineKeyboardButton("Thank you for reminding me", callback_data='reminder_job_not_done')

    keyboard.add(button_1, button_2)

    return keyboard

def quickstart_add_document_menu(language):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row_width = 1

    if language == 'russian':
        button_1 = types.InlineKeyboardButton("Хочу!", callback_data='quickstart_add_document')
    elif language == 'english':
        button_1 = types.InlineKeyboardButton("Yes!", callback_data='quickstart_add_document')

    keyboard.add(button_1)

    return keyboard

def quickstart_finalize_case_menu(language):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row_width = 1

    if language == 'russian':
        button_1 = types.InlineKeyboardButton("Давай!", callback_data='quickstart_finalize_case')
    elif language == 'english':
        button_1 = types.InlineKeyboardButton("Sure!", callback_data='quickstart_finalize_case')

    keyboard.add(button_1)

    return keyboard