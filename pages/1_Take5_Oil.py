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
import hmac

st.set_page_config(layout="wide")

# if not T5f.check_password():
    # st.stop()  # Do not continue if check_password is not True.

# # Main Streamlit app starts here
# st.write("Here goes your normal Streamlit app...")
# st.button("Click me")

# Main app logic
# if 'authenticated' not in st.session_state:
#     st.session_state.authenticated = False

# if T5f.is_authenticated():
#     st.success("You are authenticated!")
#     st.write("Your secured content goes here...")
# else:
#     st.warning("Please enter the password to access the content.")
#     password_input = st.text_input("Password", type="password")
#     if st.button("Submit"):
#         T5f.authenticate(password_input)


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
df_new = df[(df['monthdt'] >= startdate) & (df['monthdt'] <= enddate) & (df.location.isin(options))]

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


####### Create BOXES Showing comparison for previous month and vs. budget for ARO, CPD, LHPC,.... 

row0 = st.columns(6)
row1 = st.columns(6)
row2 = st.columns(6)
row3 = st.columns(6)
row4 = st.columns(6)
row5 = st.columns(6)
row6 = st.columns(6)
row7 = st.columns(6)

# ARO	CPD  	LHPC	P-Mix %	  Big 5 %	Bay Times
ind = [( 2, 'ARO'),( 1, 'CPD'),(51, 'LHPC'),(61, 'P-Mix %'),(62, 'Big 5 %'),(63, 'Bay Times')]

last2mos = pivot_df.iloc[:,-5:-3].loc[ind,:]
last2mos['diffs'] = last2mos.iloc[:,1].sub(last2mos.iloc[:,0], axis = 0) 
last2mos['diffperc'] = last2mos['diffs'] / last2mos.iloc[:,0]
last2mos = last2mos.reset_index().drop(columns=['Account_Num', 'Account'])
last2mos.index = pd.RangeIndex(start=0, stop=len(last2mos), step=1)

formatting = [
    (0, dollar_format),
    (1, dollar_format),
    (2, format_two_decimals),
    (3, perc_format),
    (4, perc_format),
    (5, format_two_decimals),
]

for index, func in formatting:
    last2mos.iloc[index, 1] = func(last2mos.iloc[index, 1])
    # last2mos.loc[index, 'values'] = last2mos[index][2]

st.write(last2mos)
cnt = 0
for col in row0:
    tile = col.container()#height=60)
    tile.write(ind[cnt][1])
    cnt += 1


cnt = 0
for col in row1:
    tile = col.container(height=200)
    tile.write(last2mos.iloc[cnt,1])
    tile.write("All")
    tile.write(arrow_format(last2mos.iloc[cnt]['diffperc']))
    tile.write('(placeholder budget)')
    cnt += 1

ind = (df['monthdt'] >= enddate - pd.DateOffset(months=1)) & (df['monthdt'] <= enddate)
df_loc = df_new[ind].groupby(['location','monthdt'])['value'].mean()#.reset_index()
st.write(df_loc)
    # + row2 + row3 + row4+ row5 + row6 + row7:
    # tile = col.container(height=60)
    # tile.title(":balloon:")


# ind_sum = [(11, 'Revenue'),    (12, 'Gross Profit'), (25, '4-Wall EBITDA'), 
#             (26, '4-Wall FCF'), (27, 'Net Profit'),   (71, '# of Cars Serviced')    ]
# ind_avg = [( 1, 'CPD'),            ( 2, 'ARO'),              (21, 'Labor %'),
#             (22, 'Controllable %'),(23, 'Uncontrollable %'), (31, 'Cash'),
#             (41, 'Gross Profit %'),(42, '4-Wall EBITDA %'),  (43, '4-Wall FCF %'),
#             (44, 'Net Profit %'),  (51, 'LHPC'),             (52, 'Revenue Per Employee Hours Worked'),
#             (61, 'P-Mix %'),       (62, 'Big 5 %'),          (63, 'Bay Times'),
#             (64, 'Discount %'),    (72, 'Gross Profit Per Car'), (73, '4-Wall EBITDA Per Car')]


############################## FROM CHATGPT ##############################
# # Assuming last2mos and ind are defined
# # last2mos = pd.DataFrame({...})
# # ind = [...]

# # Define the number of rows and columns
# num_rows = 8
# num_cols = 6

# # Initialize a dictionary to store the containers
# grid = {}

# # Create the grid of containers
# for row in range(num_rows):
#     grid[row] = st.columns(num_cols)

# # Example data (you can replace this with your actual data)
# last2mos = pd.DataFrame({
#     'col1': ['Data11', 'Data12', 'Data13', 'Data14', 'Data15', 'Data16'],
#     'diffperc': [10, 20, 30, 40, 50, 60]
# })
# ind = [['', 'Ind1'], ['', 'Ind2'], ['', 'Ind3'], ['', 'Ind4'], ['', 'Ind5'], ['', 'Ind6']]

# # Fill the first row with ind data
# for col in range(num_cols):
#     tile = grid[0][col].container()
#     if col < len(ind):
#         tile.write(ind[col][1])

# # Fill the second row with last2mos data and additional information
# for col in range(num_cols):
#     tile = grid[1][col].container()
#     if col < len(last2mos):
#         tile.write(last2mos.iloc[col, 1])
#         tile.write("All")
#         tile.write(f"DiffPerc: {last2mos.iloc[col]['diffperc']}%")
#         tile.write('(placeholder budget)')

# # You can continue to fill other rows in a similar manner