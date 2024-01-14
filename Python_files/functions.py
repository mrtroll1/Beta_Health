import os
import mysql.connector
import telebot

MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD')

def get_item_from_table_by_key(table, item, key_column, key_value):
    db_connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password=MYSQL_PASSWORD,
        database="..."
    )
    db_cursor = db_connection.cursor()

    query = f"SELECT {item} FROM {table} WHERE {key_column} = %s"
    db_cursor.execute(query, (key_value,))
    result = db_cursor.fetchone()
    
    db_cursor.close()
    db_connection.close()

    return result[0] if result else None

def add_user_name(user_id, user_name):
    db_connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password=MYSQL_PASSWORD,
        database="..."
    )
    db_cursor = db_connection.cursor()
    
    query = "INSERT INTO user_names (user_id, user_name) VALUES (%s, %s)"
    
    db_cursor.execute(query, (user_id, user_name))
    
    db_connection.commit() 
    db_cursor.close()
    db_connection.close()

def save_case(user_id, case):
    db_connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password=MYSQL_PASSWORD,
        database="..."
    )
    db_cursor = db_connection.cursor()

    # query = "INSERT INTO cases ... (%s, ...)"

    # db_cursor.execute(query, (case, ...))

    db_connection.commit()
    db_cursor.close()
    db_connection.close()

def show_cases_list(user_id):
    db_connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password=MYSQL_PASSWORD,
        database="..."
    )
    db_cursor = db_connection.cursor()

    # query = SELECT case_name FROM cases WHERE user_id == user_id

    # db_cursor.execute(query)

    db_connection.commit()
    db_cursor.close()
    db_connection.close()

def continue_case(user_id, case):
    db_connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password=MYSQL_PASSWORD,
        database="..."
    )
    db_cursor = db_connection.cursor()

    # query = SELECT case_data FROM cases where case_id == case_id

     # db_cursor.execute(query)

     db_connection.commit()
     db_cursor.close()
     db_connection.close()