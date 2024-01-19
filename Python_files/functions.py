import os
import mysql.connector

MYSQL_HOST = "localhost"
MYSQL_USER = "root"
MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD') 
MYSQL_DATABASE = "Beta_Health_db" 
MYSQL_PORT = 3307

def get_item_from_table_by_key(item, table, key_column, key_value):
    db_connection = mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        port=MYSQL_PORT
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
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        port=MYSQL_PORT
    )
    db_cursor = db_connection.cursor()
    
    query = "INSERT INTO user_names (user_id, user_name) VALUES (%s, %s)"
    
    db_cursor.execute(query, (user_id, user_name))
    
    db_connection.commit() 
    db_cursor.close()
    db_connection.close()

def add_user_doctor(doctor_id, user_id, doctor_name):
    db_connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password=MYSQL_PASSWORD,
        database="Beta_Health_db",
        port = 3307
    )
    db_cursor = db_connection.cursor()

    query = "INSERT INTO user_doctors (doctor_id, user_id, doctor_name) VALUES (%s, %s, %s)"
    
    db_cursor.execute(query, (doctor_id, user_id, doctor_name))
    
    db_connection.commit() 
    db_cursor.close()
    db_connection.close()

def add_user_case(case_name, user_id, doctor_id, case_status, case_data):
    db_connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password=MYSQL_PASSWORD,
        database="Beta_Health_db",
        port = 3307
    )
    db_cursor = db_connection.cursor()

    query = "INSERT INTO user_cases (case_name, user_id, doctor_id, case_status, case_data) VALUES (%s, %s, %s, %s, %s)"

    db_cursor.execute(query, (case_name, user_id, doctor_id, case_status, case_data))

    db_connection.commit()
    db_cursor.close()
    db_connection.close()

