import streamlit as st
import pymysql
import os
# from dotenv import load_dotenv
# load_dotenv('.env')  # take environment variables from .env.
import datetime
import T5_funcs as T5f
import take5_functions as t5f
import pandas as pd
import numpy as np
from dash import Dash, html
import dash_ag_grid as dag 
from st_aggrid import AgGrid


# Get the directory of the current script
cwdir = os.path.dirname(__file__)
# st.write(cwdir)
controlmap = pd.read_excel(cwdir + '\control_map.xlsx', index_col=None)

# get secrets from st.secrets
host = st.secrets["host"]#os.getenv('host') 
user = st.secrets["user"]#os.getenv('user')
port = st.secrets["port"]#os.getenv('port')
password = st.secrets["password"]#os.getenv('password')
databasename = st.secrets["databasename"]#os.getenv('databasename')

# read in data
connection = T5f.make_connection(host, user, port, password, databasename)
df = T5f.read_in_SQL(connection)


# st.dataframe(df.head())

maxdate = max(df.monthdt)
mindate = maxdate - pd.DateOffset(months=12)

col1, col2 = st.columns(2)
with col1:
        startdate = st.date_input("Please enter a starting date (must pick 1st of month):", mindate.date())
with col2:
        enddate = st.date_input("Please enter a ending date:", maxdate.date())

startdate = pd.to_datetime(startdate)
enddate = pd.to_datetime(enddate)

df_new = df[(df['monthdt'] >= startdate) & (df['monthdt'] <= enddate)]


pivot_df = t5f.create_T5_PL_ALL_pivot_table(result_df=df_new, controlmap=controlmap)

st.dataframe(pivot_df)

st.write('Here is the dataframe with AG GRID')

AgGrid(pivot_df, height=800)

