import streamlit as st
import pymysql
import os
# from dotenv import load_dotenv
# load_dotenv('.env')  # take environment variables from .env.
import datetime
import T5_funcs as T5f
# import take5_functions as t5f
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


st.set_page_config(layout="wide", initial_sidebar_state="collapsed")
# st.set_page_config()


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

# st.write(workdays)
extra['Date'] = pd.to_datetime(extra.Date, format='%y-%b', errors='coerce')
workdays['date'] = pd.to_datetime(workdays.date, format='%y-%b', errors='coerce')#.dt.strftime('%b %y')
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
                     id_vars=['Location', 'location', 'Date'],   # others: Pmix_perc	Big5_perc	BayTimes
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

###### make Gauges ################
size = "<span style='font-size:0.75em'>"
fig = go.Figure()
gauge_dict = {
    "titles": ["CPD Growth % MoM", "ARO Growth % MoM", "LHPC % MoM", "4-Wall EBITDA % MoM",
                "Labor % MoM", "Controllable Costs % MoM", 
                "Uncontrollable Costs % MoM",
                "Discount % MoM"]}

# CPD %
df11 = pivot_df.loc[(1,'CPD')].iloc[:-3]
df1 = df11.pct_change().round(3).dropna()
st.write(df11)
min1, max1 = min(df1), max(df1)
fig.add_trace(go.Indicator(
    title={'text': size + gauge_dict['titles'][0]},
    value = df1[-1] *100,
    delta = {
        'reference': df11[-1] - df11[-2] ,  
        'valueformat': ".0f",         # Format the delta value with one decimal place
        'suffix': " cars"    # 'prefix': "$"            
    },
    number={'suffix': "%"},  # Add percentage sign
    gauge = {'axis': {'visible': True, 'range': [min1 * 100, max1 * 100]}}, domain = {'row': 0, 'column': 0}))

# ARO %
df11 = pivot_df.loc[(2,'ARO')].iloc[:-3]
# st.write(df1)
# st.write(df1.pct_change())
df1 = df11.pct_change().round(3).dropna()
min1, max1 = min(df1), max(df1)
fig.add_trace(go.Indicator(
    title={'text': size + gauge_dict['titles'][1]},
    value = df1[-1] *100,
    delta = {'reference': df11[-1] },
    number={'suffix': "%"},  # Add percentage sign
    gauge = {'axis': {'visible': True, 'range': [min1* 100, max1* 100]}}, domain = {'row': 0, 'column': 1}))

# LHPC %
df11 = pivot_df.loc[(51,'LHPC')].iloc[:-3]
df1 = df11.pct_change().round(3).dropna()
min1, max1 = min(df1), max(df1)
fig.add_trace(go.Indicator(
    title={'text': size + gauge_dict['titles'][2]},
    value = df1[-1]*100,
    delta = {'reference': df11[-1]},
    number={'suffix': "%"},  # Add percentage sign
    gauge = {'axis': {'visible': True, 'range': [min1*100, max1*100]}}, domain = {'row': 0, 'column': 2}))

df11 = pivot_df.loc[(25,'4-Wall EBITDA')].iloc[:-3]
df1 = df11.pct_change().round(3).dropna()
min1, max1 = min(df1), max(df1)
fig.add_trace(go.Indicator(
    title={'text': size + gauge_dict['titles'][3]},
    value = df1[-1]*100,
    delta = {'reference': df11[-1]},
    number={'suffix': "%"},  # Add percentage sign
    gauge = {'axis': {'visible': True, 'range': [min1*100, max1*100]}}, domain = {'row': 0, 'column': 3}))

df11 = pivot_df.loc[(21,'Labor %')].iloc[:-3]
df1 = df11.pct_change().round(3).dropna()
min1, max1 = min(df1), max(df1)
fig.add_trace(go.Indicator(
    title={'text': size + gauge_dict['titles'][4]},
    value = df1[-1]*100,
    delta = {'reference': df11[-1]},
    number={'suffix': "%"},  # Add percentage sign
    gauge = {'axis': {'visible': True, 'range': [min1*100, max1*100]}}, domain = {'row': 1, 'column': 0}))

df11 = pivot_df.loc[(22,'Controllable %')].iloc[:-3]
df1 = df11.pct_change().round(3).dropna()
min1, max1 = min(df1), max(df1)
fig.add_trace(go.Indicator(
    title={'text': size + gauge_dict['titles'][5]},
    value = df1[-1]*100,
    delta = {'reference': df11[-1]},
    number={'suffix': "%"},  # Add percentage sign
    gauge = {'axis': {'visible': True, 'range': [min1*100, max1*100]}}, domain = {'row': 1, 'column': 1}))

df11 = pivot_df.loc[(23,'Uncontrollable %')].iloc[:-3]
df1 = df11.pct_change().round(3).dropna()
min1, max1 = min(df1), max(df1)
fig.add_trace(go.Indicator(
    title={'text': size + gauge_dict['titles'][6]},
    value = df1[-1]*100,
    delta = {'reference': df11[-1]},
    number={'suffix': "%"},  # Add percentage sign
    gauge = {'axis': {'visible': True, 'range': [min1*100, max1*100]}}, domain = {'row': 1, 'column': 2}))

df11 = pivot_df.loc[(64,'Discount %')].iloc[:-3]
df1 = df11.pct_change().round(3).dropna()
min1, max1 = min(df1), max(df1)
fig.add_trace(go.Indicator(
    title={'text': size + gauge_dict['titles'][7]},
    value = df1[-1]*100,
    delta = {'reference': df11[-1]},
    number={'suffix': "%"},  # Add percentage sign
    gauge = {'axis': {'visible': True, 'range': [min1*100, max1*100]}}, domain = {'row': 1, 'column': 3}))

fig.update_layout(
    grid = {'rows': 2, 'columns': 4, 'pattern': "independent"},
    template = {'data' : {'indicator': [{
        'mode' : "number+delta+gauge"}]
                         }})

st.plotly_chart(fig)


## display Dataframe

# def highlight_gross_profit(s):
#     if s['Account_Num'] == 12:  # Check if 'Account' is 'Gross Profit'
#         return [s[0]] + [f'${x:,.0f}' for x in s[1:]]  # Keep 'Account' as text, format others as currency
#     return s
# # Apply the formatting to the dataframe
# styled_df = pivot_df.style.apply(highlight_gross_profit, axis=1)
# # Display the styled dataframe in Streamlit
# st.write(styled_df)

pivot_df2 = T5f.clean_pivot(pivot_df)

st.dataframe(pivot_df2) #, st.column_config.NumberColumn("Dollar values”, format=”$ %d"))

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



####### Create BOXES Showing comparison for previous month and vs. budget for ARO, CPD, LHPC,.... 
box_height = 140

row0 = st.columns(6)
row1 = st.columns(6)

# ARO	CPD  	LHPC	P-Mix %	  Big 5 %	Bay Times
ind = [( 2, 'ARO'),( 1, 'CPD'),(51, 'LHPC'),(61, 'P-Mix %'),(62, 'Big 5 %'),(63, 'Bay Times')]

last2mos = pivot_df.iloc[:,-5:-3].loc[ind,:]
last2mos['diffs'] = last2mos.iloc[:,1].sub(last2mos.iloc[:,0], axis = 0) 
last2mos['diffperc'] = last2mos['diffs'] / last2mos.iloc[:,0]
last2mos = last2mos.reset_index().drop(columns=['Account_Num', 'Account'])
last2mos.index = pd.RangeIndex(start=0, stop=len(last2mos), step=1)

formatting = [
    (0, dollar_form),
    (1, format_two_decimals),
    (2, format_two_decimals),
    (3, pmix_form),
    (4, big5_form),
    (5, baytime_form),
]
for index, func in formatting:
    last2mos.iloc[index, 1] = func(last2mos.iloc[index, 1])
    # last2mos.loc[index, 'values'] = last2mos[index][2]
cnt = 0
for col in row0:
    tile = col.container()#height=60)
    tile.write(ind[cnt][1])
    cnt += 1

cnt = 0
for col in row1:
    tile = col.container(height=box_height)
    if cnt in [2, 5]:
        tile.write(last2mos.iloc[cnt,1] + arrow_form_perc_opp(last2mos.iloc[cnt]['diffperc']))
    else: 
        tile.write(last2mos.iloc[cnt,1] + arrow_form_perc(last2mos.iloc[cnt]['diffperc']))
    tile.write("All")
    tile.write('(budget #s)')
    cnt += 1

ind = (df['monthdt'] >= enddate - pd.DateOffset(months=1)) & (df['monthdt'] <= enddate)
df2months = df[ind]

# calc ARO dataframe by location
aro_df = df_rev / ext_cars_loc
aro_df = aro_df.reset_index()
ind = (aro_df['monthdt'] >= enddate - pd.DateOffset(months=1)) & (aro_df['monthdt'] <= enddate)
aro_df = aro_df[ind].groupby(['location','monthdt'])['value'].mean().reset_index()
aro_df = aro_df.pivot_table(index=['location'], columns='monthdt', values='value', aggfunc='mean')
aro_df.columns = aro_df.columns.strftime('%b %y')
aro_df['diffs'] = aro_df.iloc[:,1].sub(aro_df.iloc[:,0], axis = 0)
aro_df['diffperc'] = aro_df['diffs'] / aro_df.iloc[:,0]

### calculate CPD and LHPC for last month
ind = (ext_sum['Date'] >= enddate - pd.DateOffset(months=1)) & (ext_sum['Date'] <= enddate)
ext2_sum  = ext_sum.loc[ind,:]
ext2_sum = ext2_sum.merge(workdays, left_on='Date', right_on='date')
# get number of stores that are serving cars by month
ind = (ext2_sum.metric == 'CarsServ')  
n_stores_df = ext2_sum.loc[ind,:].Date.value_counts().reset_index()  # get number of stores open by month
ext2_sum = ext2_sum.merge(n_stores_df, left_on='Date', right_on='Date')
ext2_sum = ext2_sum.pivot_table(index=['location','Date','workdays','count'], columns = ['metric'], values='value', aggfunc='mean').reset_index()
ext2_sum['CPD'] = (ext2_sum.CarsServ / ext2_sum.workdays) #/ ext2_sum['count']
ext2_sum['LHPC'] = ext2_sum.EmpHours / ext2_sum.CarsServ 

# st.write(ext2_sum) 
### CPD df
cpd_df = ext2_sum.pivot_table(index=['location'], columns='Date', values='CPD', aggfunc='mean')#.reset_index()
cpd_df.columns = cpd_df.columns.strftime('%b %y')
cpd_df['diffs'] = cpd_df.iloc[:,1].sub(cpd_df.iloc[:,0], axis = 0) 
cpd_df['diffperc'] = cpd_df['diffs'] / cpd_df.iloc[:,0]
### LHPC df
lhpc_df = ext2_sum.pivot_table(index=['location'], columns='Date', values='LHPC', aggfunc='mean')#.reset_index()
lhpc_df.columns = lhpc_df.columns.strftime('%b %y')
lhpc_df['diffs'] = lhpc_df.iloc[:,1].sub(lhpc_df.iloc[:,0], axis = 0) 
lhpc_df['diffperc'] = lhpc_df['diffs'] / lhpc_df.iloc[:,0]

## get Pmix, Big5%, Bay Times
ind = (ext_avg['Date'] >= enddate - pd.DateOffset(months=1)) & (ext_avg['Date'] <= enddate)

ext2_avg = ext_avg.loc[ind,:]
# st.write("ext2:", ext2_avg)
ext2_avg = ext2_avg.groupby(['location','metric','Date'])['value'].mean().reset_index()
ext2_avg = ext2_avg.pivot_table(index=['location','metric'], columns='Date', values='value', aggfunc='mean')#.reset_index()
ext2_avg.columns = ext2_avg.columns.strftime('%b %y')
ext2_avg['diffs'] = ext2_avg.iloc[:,1].sub(ext2_avg.iloc[:,0], axis = 0) 
ext2_avg['diffperc'] = ext2_avg['diffs'] / ext2_avg.iloc[:,0]

# Sort by the second column
sec_col = ext2_avg.columns[1]  # get the most recent month
ext2_avg = ext2_avg.reset_index()
aro_df = aro_df.sort_values(by=sec_col, ascending=False).reset_index()
cpd_df = cpd_df.sort_values(by=sec_col, ascending=False).reset_index()
lhpc_df = lhpc_df.sort_values(by=sec_col, ascending=True).reset_index()

pmix_df = ext2_avg.loc[ext2_avg.metric == 'Pmix_perc'].sort_values(by=sec_col, ascending=False).reset_index()
big5_df = ext2_avg.loc[ext2_avg.metric == 'Big5_perc'].sort_values(by=sec_col, ascending=False).reset_index()
baytime_df = ext2_avg.loc[ext2_avg.metric == 'BayTimes'].sort_values(by=sec_col, ascending=True).reset_index()


# Initialize a dictionary to store the containers
grid = {}
# # Define the number of rows and columns
num_rows = len(options)
num_cols = 6

# # Create the grid of containers
for row in range(num_rows):
    grid[row] = st.columns(num_cols)
#### ARO
for row in range(num_rows):
    tile = grid[row][0].container(height=box_height)
    tile.write(dollar_form(aro_df.loc[row,sec_col]) + arrow_form_num(aro_df.iloc[row]['diffs']))
    tile.write(aro_df.loc[row,'location'])
    tile.write('(budget #s)')
#### CPD
for row in range(num_rows):
    tile = grid[row][1].container(height=box_height)
    tile.write(numb_form(cpd_df.loc[row,sec_col]) + arrow_form_num(cpd_df.iloc[row]['diffs']))
    tile.write(cpd_df.loc[row,'location'])
    tile.write('(budget #s)')
#### LHPC
for row in range(num_rows):
    tile = grid[row][2].container(height=box_height)
    tile.write(format_two_decimals(lhpc_df.loc[row,sec_col]) + arrow_form_num_opp(lhpc_df.iloc[row]['diffs']))
    tile.write(lhpc_df.loc[row,'location'])
    tile.write('(budget #s)')
#### PMix %
for row in range(num_rows):
    tile = grid[row][3].container(height=box_height)
    tile.write(pmix_form(pmix_df.loc[row,sec_col]) + arrow_form_perc(pmix_df.iloc[row]['diffs']))
    tile.write(pmix_df.loc[row,'location'])
    tile.write('(budget #s)')
#### Big 5%
for row in range(num_rows):
    tile = grid[row][4].container(height=box_height)
    tile.write(big5_form(big5_df.loc[row,sec_col]) + arrow_form_perc(big5_df.iloc[row]['diffs']))
    tile.write(big5_df.loc[row,'location'])
    tile.write('(budget #s)')
#### Bay Times
for row in range(num_rows):
    tile = grid[row][5].container(height=box_height)
    tile.write(baytime_form(baytime_df.loc[row,sec_col]) + arrow_form_num_opp(baytime_df.iloc[row]['diffs']))
    tile.write(baytime_df.loc[row,'location'])
    tile.write('(budget #s)')




### Test Area
st.markdown("### Test Area - Future Improvements")
############################# Trend line test (linear)
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
