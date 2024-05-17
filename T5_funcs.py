'''
Helper functions to create, add entries, etc. for T5 Oil
'''
import pymysql
import streamlit as st
import pandas as pd

def make_connection(host,user,port,password,databasename):
    connection = pymysql.connect(host=host,user=user,port=port, 
                            password=password,database=databasename)
    return connection


def read_in_SQL(connection):
    # SQL query to read data
    query = "SELECT * FROM T5_fin_data"
    try:
        # with connection:
        #     with connection.cursor() as cursor:
        #         cursor.execute("SET SESSION innodb_lock_wait_timeout = 600;")  # Set to 600 seconds
        #         connection.commit()
        # Read data into a Pandas DataFrame
        df = pd.read_sql(query, connection)
        return df
    except Exception as e:
        print(f"An error occurred: {e}")
    



