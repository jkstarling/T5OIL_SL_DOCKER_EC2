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
import plotly.express as px
from dash import Dash, html
import dash_ag_grid as dag 
from st_aggrid import AgGrid
from helper import *

st.set_page_config(layout="wide")

# Get the directory of the current script
cwdir = os.path.dirname(__file__)
cwdirup1 = os.path.dirname(cwdir)
# st.write(cwdir)
controlmap = pd.read_excel(cwdir + '\control_map.xlsx', index_col=None)
extra = pd.read_csv(cwdirup1 + '\\t5_extra_data.csv', index_col=None)
workdays = pd.read_csv(cwdirup1 + '\\t5_workdays.csv', index_col=None)

locations = [(1402,'1402 - Ten Mile'), 
            (1403, '1403 - Caldwell'), 
            (1404, '1404 - Glenwood'), 
            (1405, '1405 - Ontario'), 
            (1407, '1407 - Pasco'), 
            (1881, '1881 - Lacey')]
loc_df = pd.DataFrame(locations, columns=['Location', 'location'])
loc_df['Location'] = loc_df['Location'].astype('int64')

extra = extra.merge(loc_df, how='left', on='Location')

extra['Date'] = pd.to_datetime(extra.Date, format='%y-%b', errors='coerce')
workdays['date'] = pd.to_datetime(workdays.date, format='%b-%y', errors='coerce')#.dt.strftime('%b %y')
# st.write(workdays)

# get secrets from st.secrets
host = st.secrets["host"]#os.getenv('host') 
user = st.secrets["user"]#os.getenv('user')
port = st.secrets["port"]#os.getenv('port')
password = st.secrets["password"]#os.getenv('password')
databasename = st.secrets["databasename"]#os.getenv('databasename')

#### read in data
connection = T5f.make_connection(host, user, port, password, databasename)
df = T5f.read_in_SQL(connection)

# select locations
options = st.multiselect('Select the Take 5 Oil Locations you want to perform analsysis on:', 
                        df.location.unique(), df.location.unique())



#### get data within dates. Baseline is 13 months.
maxdate = max(df.monthdt)
mindate = maxdate - pd.DateOffset(months=12)

col1, col2 = st.columns(2)
with col1:
        startdate = st.date_input("Please enter a starting date (must pick 1st of month):", mindate.date())
with col2:
        enddate = st.date_input("Please enter a ending date:", maxdate.date())

startdate = pd.to_datetime(startdate)
enddate = pd.to_datetime(enddate)

ext_melt = pd.melt(extra, 
                     id_vars=['Location', 'location', 'Date'], 
                     var_name='metric', 
                     value_name='value').dropna(subset=['value'])
ext_melt = ext_melt[(ext_melt.location.isin(options))]

ext_avg = ext_melt[(ext_melt['Date'] >= startdate) & 
                   (ext_melt['Date'] <= enddate) & 
                   (ext_melt.metric.isin(['BayTimes','Pmix_perc','Big5_perc']))]
ext_sum = ext_melt[(ext_melt['Date'] >= startdate) & 
                   (ext_melt['Date'] <= enddate) & 
                   (ext_melt.metric.isin(['CarsServ','EmpHours']))]

df_new = df[(df['monthdt'] >= startdate) & (df['monthdt'] <= enddate) & (df.location.isin(options))]

workdays = workdays[(workdays['date'] >= startdate) & 
                    (workdays['date'] <= enddate)]
# st.write(ext_melt)
# st.write(df_new.dtypes)
# st.write(df_new)

pivot_df = T5f.create_T5_pivot_table(result_df=df_new, ext_avg=ext_avg, 
                                     ext_sum=ext_sum, controlmap=controlmap,
                                     workdays=workdays)

st.dataframe(pivot_df)

# st.write('Here is the dataframe with AG GRID')
# AgGrid(pivot_df, height=800)

# st.write(df_new)


ind = (df_new.Account_Num >4000) & (df_new.Account_Num <4999)
df_rev = df_new[ind].groupby(['location','monthdt'])['value'].sum().reset_index()
# st.write(df_rev)

c1, c2 = st.columns(2)

with c1:
    st.header("Overall Revenue Trendline")
    fig = px.line(df_rev, x='monthdt', y='value', color='location', title="Revenue by Location")
    st.plotly_chart(fig)

# Upper-right column (UR): Cars Serviced by Location
with c2:
    ext_cars_by_loc = ext_melt[ext_melt.metric == 'CarsServ']
    st.header("Cars Serviced by Location")
    fig = px.bar(ext_melt, x='Date', y='value', color='location', title="Cars Serviced by Location")
    st.plotly_chart(fig)

# st.write(ext_cars_by_loc)