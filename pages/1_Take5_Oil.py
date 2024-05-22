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
import plotly.graph_objects as go
from dash import Dash, html
import dash_ag_grid as dag 
from st_aggrid import AgGrid
from helper import *
from sklearn.linear_model import LinearRegression


st.set_page_config(layout="wide")

# Get the directory of the current script
cwdir = os.path.dirname(__file__)
cwdirup1 = os.path.dirname(cwdir)
# st.write(cwdir)
try: controlmap = pd.read_excel(cwdir + '\control_map.xlsx', index_col=None)
except: controlmap = pd.read_excel(cwdir + '/control_map.xlsx', index_col=None)

try: extra = pd.read_csv(cwdirup1 + '\\t5_extra_data.csv', index_col=None)
except: extra = pd.read_csv(cwdirup1 + '/t5_extra_data.csv', index_col=None)

try: workdays = pd.read_csv(cwdirup1 + '\\t5_workdays.csv', index_col=None)
except: workdays = pd.read_csv(cwdirup1 + '/t5_workdays.csv', index_col=None)

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

df = df.loc[(df.location != 'Admin') & (df.location != 'Not Specified') & (df.location != 'Saranac'),:]


#### get data within dates. Baseline is 13 months.
maxdate = max(df.monthdt)
mindate = maxdate - pd.DateOffset(months=12)

with st.sidebar:
    options = st.multiselect('Select the Take 5 Oil Locations you want to perform analsysis on:', 
                            df.location.unique(), df.location.unique())
    startdate = st.date_input("Please enter a starting date (must pick 1st of month):", mindate.date())
    enddate = st.date_input("Please enter a ending date:", maxdate.date())
startdate = pd.to_datetime(startdate)
enddate = pd.to_datetime(enddate)

# trim data based on selected/standard dates
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


#### create monthly pivot table and display. 
pivot_df = T5f.create_T5_pivot_table(result_df=df_new, ext_avg=ext_avg, 
                                     ext_sum=ext_sum, controlmap=controlmap,
                                     workdays=workdays)

st.dataframe(pivot_df)


# st.write('Here is the dataframe with AG GRID')
# AgGrid(pivot_df, height=800)


###### crate dataframes for figures
#### create revenue by location dataframe
ind = (df_new.Account_Num >4000) & (df_new.Account_Num <4999)
df_rev = df_new[ind].groupby(['location','monthdt'])['value'].sum()#.reset_index()
tot_rev_by_date = df_rev.reset_index().groupby('monthdt')['value'].sum().reset_index()


#### create # of cars serviced dataframe
ext_cars_by_loc = ext_melt[ext_melt.metric == 'CarsServ']
tot_cars_by_date = ext_cars_by_loc.groupby('Date')['value'].sum().reset_index()

#### create gross profit dataframe
ind = (df_new.Account_Num >5000) & (df_new.Account_Num <5998)
df_cogs = df_new[ind].groupby(['location','monthdt'])['value'].sum()#.reset_index()
df_gross = df_rev - df_cogs
tot_gross_by_date = df_gross.reset_index().groupby('monthdt')['value'].sum().reset_index()
# st.write(df_gross)

#### create 4-wall EBITDA dataframe
ind = (df_new.Account_Num >6000) & (df_new.Account_Num <7999)
df_4wexpenses = df_new[ind].groupby(['location','monthdt'])['value'].sum()#.reset_index()
df_4webitda = df_gross - df_4wexpenses
tot_ebitda_by_date = df_4webitda.reset_index().groupby('monthdt')['value'].sum().reset_index()

#### create Cash dataframe
ind = (df_new.Account_Num >1000) & (df_new.Account_Num <1099)
df_cash = df_new[ind].groupby(['location','monthdt'])['value'].sum()#.reset_index()
tot_cash_by_date = df_cash.reset_index().groupby('monthdt')['value'].sum().reset_index()

#### create 4-wall EBITDA per car dataframe
# st.write(ext_cars_by_loc)
# st.write(df_4webitda)
extcarsloc = ext_cars_by_loc.copy()
extcarsloc.rename(columns={'Date': 'monthdt'}, inplace=True)
ext_cars_loc = extcarsloc.set_index(['location','monthdt'])['value']
df_ebitda_by_car = df_4webitda / ext_cars_loc
# st.write(df_ebitda_by_car)
tot_ebitdacar_by_date = df_ebitda_by_car.reset_index().groupby('monthdt')['value'].sum().reset_index()




c1, c2 = st.columns(2)
with c1:
    # st.header("Overall Revenue Trendline")
    fig = px.bar(df_rev.reset_index(), x='monthdt', y='value', color='location', title="Revenue by Location")
    fig.add_scatter(x=tot_rev_by_date['monthdt'], y=tot_rev_by_date['value'], mode='lines+markers', name='Total')
    st.plotly_chart(fig)

    # st.header("Gross Profit Trendline")
    fig3 = px.bar(df_gross.reset_index(), x='monthdt', y='value', color='location', title="Gross Profit by Location")
    fig3.add_scatter(x=tot_gross_by_date['monthdt'], y=tot_gross_by_date['value'], mode='lines+markers', name='Total')
    st.plotly_chart(fig3)

    # st.header("Cash Trendline")
    fig5 = px.bar(df_cash.reset_index(), x='monthdt', y='value', color='location', title="Gross Profit by Location")
    fig5.add_scatter(x=tot_cash_by_date['monthdt'], y=tot_cash_by_date['value'], mode='lines+markers', name='Total')
    st.plotly_chart(fig5)

with c2:
    # Upper-right column (UR): Cars Serviced by Location
    # st.header("Cars Serviced by Location")
    fig2 = px.bar(ext_cars_by_loc, x='Date', y='value', color='location', title="Cars Serviced by Location")
    fig2.add_scatter(x=tot_cars_by_date['Date'], y=tot_cars_by_date['value'], mode='lines+markers', name='Total')
    st.plotly_chart(fig2)

    # st.header("4-Wall EBITDA Trendline")
    fig4 = px.bar(df_4webitda.reset_index(), x='monthdt', y='value', color='location', title="4-Wall EBITDA by Location")
    fig4.add_scatter(x=tot_ebitda_by_date['monthdt'], y=tot_ebitda_by_date['value'], mode='lines+markers', name='Total')
    st.plotly_chart(fig4)

    # st.header("4-Wall EBITDA per car Trendline")
    fig6 = px.bar(df_ebitda_by_car.reset_index(), x='monthdt', y='value', color='location', title="4-Wall EBITDA by Car by Location")
    fig6.add_scatter(x=tot_ebitdacar_by_date['monthdt'], y=tot_ebitdacar_by_date['value'], mode='lines+markers', name='Total')
    st.plotly_chart(fig6)



############################## Trend line test (linear)
# Prepare data for forecasting
df_grouped = ext_cars_by_loc.groupby('Date').sum().reset_index()
# Forecast for the next 3 months
future_dates = pd.date_range(start=df_grouped['Date'].max() + pd.DateOffset(months=1), periods=3, freq='M')
# Linear Regression Model for forecasting
X = np.arange(len(df_grouped)).reshape(-1, 1)
y = df_grouped['value']
model = LinearRegression()
model.fit(X, y)
# Predict the next 3 months
X_future = np.arange(len(df_grouped), len(df_grouped) + 3).reshape(-1, 1)
y_future = model.predict(X_future)
# Create a DataFrame for forecasted values
forecast_df = pd.DataFrame({
    'Date': future_dates,
    'value': y_future
})
# Combine the original and forecasted DataFrames
combined_df = pd.concat([df_grouped, forecast_df])
# Plotting
fig2 = px.bar(ext_cars_by_loc, x='Date', y='value', color='location', title="Cars Serviced by Location (w/linear regression trendline)")
# Adding the forecasted values as a line
fig2.add_scatter(x=combined_df['Date'], y=combined_df['value'], mode='lines', name='Trend Line')
st.plotly_chart(fig2)
######################################################



row1 = st.columns(6)
row2 = st.columns(6)
row3 = st.columns(6)
row4 = st.columns(6)
row5 = st.columns(6)
row6 = st.columns(6)
row7 = st.columns(6)

for col in row1 + row2 + row3 + row4+ row5 + row6 + row7:
    tile = col.container(height=60)
    tile.title(":balloon:")