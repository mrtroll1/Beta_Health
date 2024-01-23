import os
import mysql.connector
from mysql.connector import Error
import time
import uuid
import telebot
from cryptography.fernet import Fernet
import mysql.connector
from mysql.connector import Error

encoded_key = os.environ.get('FERNET_KEY')
if encoded_key is None:
    raise ValueError("No encryption key found in environment variables")

key = encoded_key.encode()
cipher_suite = Fernet(key)

def connect():
    try:
        conn = mysql.connector.connect(
            host = "127.0.0.1",
            user = "root",
            password = os.environ.get("MYSQL_PASSWORD") ,
            database = "Beta_Health" ,
            port = 3307
        )
        if conn.is_connected():
            return conn

    except Error as e:
        print(f"Error while connecting to MySQL: {e}")
        return None

def get_item_from_table_by_key(item, table, key_column, key_value):
    db_connection = connect()
    if db_connection is None:
        print("Database connection failed.")
        return None

    try:
        db_cursor = db_connection.cursor()
        query = f"SELECT {item} FROM {table} WHERE {key_column} = %s"
        db_cursor.execute(query, (key_value,))
        result = db_cursor.fetchone()

        while db_cursor.nextset():
            pass

        return result[0] if result else None
    
    except Error as e:
        print(f"Error: {e}")
        return None
    finally:
        if db_cursor:
            db_cursor.close()
        if db_connection:
            db_connection.close()


def get_itmes_from_table_by_key(item, table, key_column, key_value):
    db_connection = connect()
    if db_connection is None:
        print("Database connection failed.")
        return None

    try:
        db_cursor = db_connection.cursor()
        query = f"SELECT {item} FROM {table} WHERE {key_column} = %s"
        db_cursor.execute(query, (key_value,))
        result = db_cursor.fetchall()

        while db_cursor.nextset():
            pass

        return result if result else None
    
    except Error as e:
        print(f"Error: {e}")
        return None
    finally:
        if db_cursor:
            db_cursor.close()
        if db_connection:
            db_connection.close()

def alter_table(table, column, new_value, key_column, key_value):
    db_connection = connect()
    if db_connection is None:
        return

    try:
        db_cursor = db_connection.cursor()
        query = f"UPDATE {table} SET {column} = %s WHERE {key_column} = %s"
        db_cursor.execute(query, (new_value, key_value))
        db_connection.commit()
    except Error as e:
        print(f"Error altering table: {e}")
    finally:
        if db_connection.is_connected():
            db_cursor.close()
            db_connection.close()

def increment_value(table, column, key_column, key_value):
    db_connection = connect()
    if db_connection is None:
        print("Database connection failed.")
        return

    try:
        db_cursor = db_connection.cursor()
        query = f"UPDATE {table} SET {column} = {column} + 1 WHERE {key_column} = %s"
        db_cursor.execute(query, (key_value, ))
        db_connection.commit()
    except Error as e:
        print(f"Error altering table: {e}")
    finally:
        if db_connection.is_connected():
            db_cursor.close()
            db_connection.close()

def add_user_name(user_id, user_name):
    db_connection = connect()
    if db_connection is None:
        print("Database connection failed.")
        return

    try:
        db_cursor = db_connection.cursor()
        query = "INSERT INTO users (user_id, user_name) VALUES (%s, %s)"
        db_cursor.execute(query, (user_id, user_name))
        db_connection.commit() 
    except Error as e:
        print(f"Error: {e}")
    finally:
        if db_cursor:
            db_cursor.close()
        if db_connection:
            db_connection.close()

def add_user_doctor(doctor_id, user_id, doctor_name):
    db_connection = connect()
    if db_connection is None:
        print("Database connection failed.")
        return

    try:
        db_cursor = db_connection.cursor()
        query = "INSERT INTO user_doctors (doctor_id, user_id, doctor_name) VALUES (%s, %s, %s)"
        db_cursor.execute(query, (doctor_id, user_id, doctor_name))
        db_connection.commit() 
    except Error as e:
        print(f"Error: {e}")
    finally:
        if db_cursor:
            db_cursor.close()
        if db_connection:
            db_connection.close()

def add_user_case(case_id, case_name, user_id, case_status, case_data):
    db_connection = connect()
    if db_connection is None:
        print("Database connection failed.")
        return

    try:
        db_cursor = db_connection.cursor()
        query = "INSERT INTO user_cases (case_id, case_name, user_id, case_status, case_data) VALUES (%s, %s, %s, %s, %s)"
        db_cursor.execute(query, (case_id, case_name, user_id, case_status, case_data))
        db_connection.commit()
    except Error as e:
        print(f"Error: {e}")
    finally:
        if db_cursor:
            db_cursor.close()
        if db_connection:
            db_connection.close()



def generate_unique_filename():
    timestamp = int(time.time())
    random_str = uuid.uuid4().hex
    return f"{timestamp}_{random_str}.jpg"

def encrypt_file(file_path):
    with open(file_path, 'rb') as file_to_encrypt:
        file_data = file_to_encrypt.read()
    encrypted_data = cipher_suite.encrypt(file_data)
    with open(file_path, 'wb') as encrypted_file:
        encrypted_file.write(encrypted_data)

def save_file_to_server(downloaded_file, user_id, case_id):
    base_save_path = '/home/luka/Projects/Beta_Health/User_data/Cases'

    case_specific_path = os.path.join(base_save_path, str(case_id))
    if not os.path.exists(case_specific_path):
        os.makedirs(case_specific_path)

    unique_filename = generate_unique_filename() + '.' + file_extension
    full_path = os.path.join(case_specific_path, unique_filename)
    with open(full_path, 'wb') as file:
        file.write(downloaded_file)

    encrypt_file(full_path)
    return case_specific_path, full_path

def decrypt_file(file_path):
    try:
        with open(file_path, 'rb') as encrypted_file:
            encrypted_data = encrypted_file.read()
        decrypted_data = cipher_suite.decrypt(encrypted_data)
        with open(file_path, 'wb') as decrypted_file:
            decrypted_file.write(decrypted_data)
    except Exception as e:
        print(f'Error during decryption: {e}')
        return False
    return True






