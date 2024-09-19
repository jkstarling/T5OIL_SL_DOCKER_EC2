'''
Helper functions to create, add entries, etc. for T5 Oil
'''
import pymysql
import streamlit as st
import pandas as pd
import numpy as np
import hmac
import time
from helper import *

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
    

def filter_add_accounts(df, low_n, high_n):
    filtered_pivot_table = df[
        (df.index.get_level_values('Account_Num') > low_n) & 
        (df.index.get_level_values('Account_Num') < high_n) ]
    try:
        return filtered_pivot_table.sum(axis=0)   # Sum up along the columns
    except: 
        return 0


def create_T5_pivot_table(result_df, ext_avg, ext_sum, controlmap, workdays):
    '''
    Takes the result dataframe and the T5 location and returns 
    a pivot dataframe across all months
    '''
    # import pandas as pd
    import numpy as np

    # st.write(ext_sum)
    # ind = (ext_sum['Date'] >= enddate - pd.DateOffset(months=1)) & (ext_sum['Date'] <= enddate)
    ext2_sum  = ext_sum
    ext2_sum = ext2_sum.merge(workdays, left_on='Date', right_on='date')
    # get number of stores that are serving cars by month
    ind = (ext2_sum.metric == 'CarsServ')  
    n_stores_df = ext2_sum.loc[ind,:].Date.value_counts().reset_index()  # get number of stores open by month
    ext2_sum = ext2_sum.merge(n_stores_df, left_on='Date', right_on='Date')
    ext2_sum = ext2_sum.pivot_table(index=['location','Date','workdays','count'], columns = ['metric'], values='value', aggfunc='mean').reset_index()
    # ext2_sum['CPD'] = (ext2_sum.CarsServ / ext2_sum.workdays) / ext2_sum['count']
    # ext2_sum['LHPC'] = ext2_sum.EmpHours / ext2_sum.CarsServ 

    # st.write(ext2_sum)


    result = result_df
    # Pivot the DataFrame by 'Month', keeping columns ('Account_Num', 'Account'), summing 'value', and filtering by 'location'
    pivot_table = result.pivot_table(index=['Account_Num', 'Account'], columns='monthdt', values='value', aggfunc='sum')
    ext_avg = ext_avg.pivot_table(index=['metric'], columns='Date', values='value', aggfunc='mean')
    ext_sum = ext_sum.pivot_table(index=['metric'], columns='Date', values='value', aggfunc='sum')
    work_pivot = workdays.pivot_table( columns='date', values='workdays', aggfunc='sum')


    ### change the dt to Mmmm YYYY 
    # pivot_table.replace(0.0, np.nan, inplace=True)
    pivot_table = pivot_table.reindex(columns=pivot_table.columns.sort_values())
    pivot_table.columns = pivot_table.columns.strftime('%b %y')

    ext_avg = ext_avg.reindex(columns=ext_avg.columns.sort_values())
    ext_avg.columns = ext_avg.columns.strftime('%b %y')
    ext_sum = ext_sum.reindex(columns=ext_sum.columns.sort_values())
    ext_sum.columns = ext_sum.columns.strftime('%b %y')
    work_pivot.columns = work_pivot.columns.strftime('%b %y')

    st.write(ext_sum, work_pivot)
    # ### 1 CPD
    # st.write(ext2_sum.CarsServ)
    # st.write(ext2_sum.workdays)
    st.write(ext2_sum['count'])
    pivot_table.loc[(1, 'CPD'),:] = np.round(ext_sum.loc['CarsServ',:] / work_pivot.loc['workdays',:], 1 )/ ext2_sum['count']

    ### 11  Total Income	(sum all 4000s)
    summed_values = filter_add_accounts(pivot_table, 4000, 4999)
    pivot_table.loc[(11, 'Revenue'), :] = np.round(summed_values,0)

     ### 2 ARO
    pivot_table.loc[(2, 'ARO'),:] = np.round(pivot_table.loc[(11, 'Revenue'), :] / ext_sum.loc['CarsServ',:],0)

    ### 5998 Total Cost of Goods Sold	(sum all 5000s)
    summed_values = filter_add_accounts(pivot_table, 5000, 5998)
    pivot_table.loc[(5998, 'Total Cost of Goods Sold'), :] = summed_values
    ###  12  Gross Profit	5998  minus 11
    top = pivot_table.loc[(11, 'Revenue'), :]
    bot = pivot_table.loc[(5998, 'Total Cost of Goods Sold'), :]
    pivot_table.loc[(12, 'Gross Profit'), :] = np.round(top-bot, 0) #diff.apply(lambda x: f'${x:,.0f}') #f'${val:,.0f}'

    ### 8990  Total Expenses	(add all 6000 - 8980(inclusive))
    summed_values = filter_add_accounts(pivot_table, 6000, 8990)

    pivot_table.loc[(8990, 'Total Expenses'), :] = summed_values

    ### 8999  Net Operating Income	5999 minus 8990  
    top = pivot_table.loc[(12, 'Gross Profit'), :]
    bot = pivot_table.loc[(8990, 'Total Expenses'), :]
    pivot_table.loc[(8999, 'Net Operating Income'), :] = top - bot

    ### 9199  Total Other Income	  (add all 9100s)
    summed_values = filter_add_accounts(pivot_table, 9000, 9199)
    pivot_table.loc[(9199, 'Total Other Income'), :] = summed_values

    ### 9980  Total Other Expenses  (add all 9200s + )
    summed_values = filter_add_accounts(pivot_table, 9200, 9980)
    pivot_table.loc[(9980, 'Total Other Expenses'), :] = summed_values

    ###  9990    Net Other Income	 9199 minus  9980  
    top = pivot_table.loc[(9199, 'Total Other Income'), :]
    bot = pivot_table.loc[(9980, 'Total Other Expenses'), :]
    pivot_table.loc[(9990, 'Net Other Income'), :] = np.round(top - bot,0)

    ###  27   Net Income	           9990 plus 8999
    top = pivot_table.loc[(9990, 'Net Other Income'), :]
    bot = pivot_table.loc[(8999, 'Net Operating Income'), :]
    pivot_table.loc[(27, 'Net Profit'), :] = np.round(top + bot,0)

    # remove all 0.0s and replace with NaNs
    pivot_table.replace(0.0, np.nan, inplace=True)


    ##### create 4 wall reports #####

    # 10005	4 Wall Expenses	(all 6000 to 7999)
    summed_values = filter_add_accounts(pivot_table, 6000, 7999)
    pivot_table.loc[(10005, '4 Wall Expenses'), :] = summed_values

    # 25	4 Wall Profit	Gross Profit 5999 minus 10005
    top = pivot_table.loc[(12, 'Gross Profit'), :]
    bot = pivot_table.loc[(10005, '4 Wall Expenses'), :]
    pivot_table.loc[(25, '4-Wall EBITDA'), :] = np.round(top - bot,0)

    # 10011	Labor	(add all 6000s)
    summed_values = filter_add_accounts(pivot_table, 6000, 6999)
    pivot_table.loc[(10011, 'Labor'), :] = summed_values

    # 10012	Controllable	(add all 7000s that are CONTROLABLE)
    filtered_pivot_table = pivot_table[
        (pivot_table.index.get_level_values('Account_Num') > 7000) & 
        (pivot_table.index.get_level_values('Account_Num') < 7999)     ]
    # add along columns if Controllable
    existing_accounts = filtered_pivot_table.index.get_level_values(1)
    controllable_rows = controlmap[(controlmap['Account'].isin(existing_accounts)) & (controlmap['Controllable'] == 'Controllable')]
    account_names = controllable_rows['Account'].tolist()
    account_names = [(int(x[:4]), x) for x in account_names]
    selected_rows = filtered_pivot_table.loc[account_names,:]
    sum_along_columns = selected_rows.sum()
    pivot_table.loc[(10012, 'Controllable'), :] = sum_along_columns

    # 10013	Uncontrollable	(add all 7000s that are UNCONTROLABLE)
    filtered_pivot_table = pivot_table[
        (pivot_table.index.get_level_values('Account_Num') > 7000) & 
        (pivot_table.index.get_level_values('Account_Num') < 7999)     ]
    # add along columns if unControllable
    existing_accounts = filtered_pivot_table.index.get_level_values(1)
    controllable_rows = controlmap[(controlmap['Account'].isin(existing_accounts)) & (controlmap['Controllable'] == 'Uncontrollable')]
    account_names = controllable_rows['Account'].tolist()
    account_names = [(int(x[:4]), x) for x in account_names]
    selected_rows = filtered_pivot_table.loc[account_names,:]
    sum_along_columns = selected_rows.sum()
    pivot_table.loc[(10013, 'Uncontrollable'), :] = sum_along_columns

    # 10021	Labor %	10011 divide by  11  (11, 'Revenue')
    top = pivot_table.loc[(10011, 'Labor'), :]
    bot = pivot_table.loc[(11, 'Revenue'), :]
    pivot_table.loc[(21, 'Labor %'), :] = np.round(top / bot,2)

    # 22	Controllable %	10012 divide by  11  (11, 'Revenue')
    top = pivot_table.loc[(10012, 'Controllable'), :]
    bot = pivot_table.loc[(11, 'Revenue'), :]
    pivot_table.loc[(22, 'Controllable %'), :] = np.round(top / bot,2)

    # 23	Uncontrollable %	10013 divide by  11  (11, 'Revenue')
    top = pivot_table.loc[(10013, 'Uncontrollable'), :]
    bot = pivot_table.loc[(11, 'Revenue'), :]
    pivot_table.loc[(23, 'Uncontrollable %'), :] = np.round(top / bot,2)

    #26 4-Wall FCF
    top = pivot_table.loc[(8999, 'Net Operating Income'),:]
    bot = pivot_table.loc[(9230, '9230 Interest Expense'),:]
    pivot_table.loc[(26, '4-Wall FCF'), :] = np.round(top - bot,2)

    #31 Cash
    summed_values = filter_add_accounts(pivot_table, 1000, 1099)
    pivot_table.loc[(31, 'Cash'), :] = np.round(summed_values,0)

    #41 Gross Profit %
    top = pivot_table.loc[(12, 'Gross Profit'),:]
    bot = pivot_table.loc[(11, 'Revenue'),:]
    pivot_table.loc[(41, 'Gross Profit %'), :] = np.round(top / bot, 2)

    #42 4-WALL EBITDA %
    top = pivot_table.loc[(25, '4-Wall EBITDA'),:]
    bot = pivot_table.loc[(11, 'Revenue'),:]
    pivot_table.loc[(42, '4-Wall EBITDA %'), :] = np.round(top / bot, 2)

    #43 4-WALL FCF %
    top = pivot_table.loc[(26, '4-Wall FCF'),:]
    bot = pivot_table.loc[(11, 'Revenue'),:]
    pivot_table.loc[(43, '4-Wall FCF %'), :] = np.round(top / bot, 2)

    #44 4-WALL FCF %
    top = pivot_table.loc[(27, 'Net Profit'),:]
    bot = pivot_table.loc[(11, 'Revenue'),:]
    pivot_table.loc[(44, 'Net Profit %'), :] = np.round(top / bot, 2)

    #51 LHPC
    pivot_table.loc[(51, 'LHPC'),:] = np.round(ext_sum.loc['EmpHours', :] / ext_sum.loc['CarsServ', :],2)
    #52 Revenue Per Employee Hours Worked
    pivot_table.loc[(52, 'Revenue Per Employee Hours Worked'),:] = np.round(pivot_table.loc[(11, 'Revenue'), :] / ext_sum.loc['EmpHours', :],2)

    #61 P-Mix %
    pivot_table.loc[(61, 'P-Mix %'),:] = np.round(ext_avg.loc['Pmix_perc', :],2)
    #62 Big 5 %
    pivot_table.loc[(62, 'Big 5 %'),:] = np.round(ext_avg.loc['Big5_perc', :],2)
    #63 Bay Times
    pivot_table.loc[(63, 'Bay Times'),:] = np.round(ext_avg.loc['BayTimes', :],2)
    #64 Discount %
    summed_values = filter_add_accounts(pivot_table, 4099, 4899)
    pivot_table.loc[(64, 'Discount %'),:] = np.round(pivot_table.loc[(4900, '4900 Sales - Discounts'), :] / summed_values,2)
    
    #71 # of Cars Serviced
    pivot_table.loc[(71, '# of Cars Serviced'),:] = ext_sum.loc['CarsServ', :]
    #72 Gross Profit Per Car
    pivot_table.loc[(72, 'Gross Profit Per Car'),:] = np.round(pivot_table.loc[(12, 'Gross Profit'), :] / ext_sum.loc['CarsServ', :],2)
    #73 4-Wall EBITDA Per Car
    pivot_table.loc[(73, '4-Wall EBITDA Per Car'),:] = np.round(pivot_table.loc[(25, '4-Wall EBITDA'), :] / ext_sum.loc['CarsServ', :],2)
    
    pivot_table.replace(0.0, np.nan, inplace=True)

    # make blank rows
    for i in [10, 20, 24, 30, 40, 50, 60, 70]:
        pivot_table.loc[(i, ''), :] = [None] * len(pivot_table.columns)

    final_df = pivot_table.loc[pivot_table.index.get_level_values(0) < 100] 
    # Sort the index
    final_df.sort_index(inplace=True)

    # create the LTM and "last three months vs prev 3 months"
    last12months = final_df.iloc[:, -12:]
    last3months = final_df.iloc[:, -3:]
    prev3months = final_df.iloc[:, -6:-3]
    #indices for sum/avg rows
    ind_sum = [(11, 'Revenue'),    (12, 'Gross Profit'), (25, '4-Wall EBITDA'), 
               (26, '4-Wall FCF'), (27, 'Net Profit'),   (71, '# of Cars Serviced')    ]
    ind_avg = [( 1, 'CPD'),            ( 2, 'ARO'),              (21, 'Labor %'),
                (22, 'Controllable %'),(23, 'Uncontrollable %'), (31, 'Cash'),
                (41, 'Gross Profit %'),(42, '4-Wall EBITDA %'),  (43, '4-Wall FCF %'),
                (44, 'Net Profit %'),  (51, 'LHPC'),             (52, 'Revenue Per Employee Hours Worked'),
                (61, 'P-Mix %'),       (62, 'Big 5 %'),          (63, 'Bay Times'),
                (64, 'Discount %'),    (72, 'Gross Profit Per Car'), (73, '4-Wall EBITDA Per Car')]

    last12sum = last12months.loc[ind_sum,:].sum(axis=1)
    last12avg = last12months.loc[ind_avg,:].mean(axis=1)
    last12sum.name = 'LTM'
    last12avg.name = 'LTM'
    final_df.loc[ind_sum,'LTM'] = last12sum#.apply(lambda x: f'${x:,.0f}')
    final_df.loc[ind_avg,'LTM'] = last12avg

    last3sum = last3months.loc[ind_sum,:].sum(axis=1)
    last3avg = last3months.loc[ind_avg,:].mean(axis=1)
    prev3sum = prev3months.loc[ind_sum,:].sum(axis=1)
    prev3avg = prev3months.loc[ind_avg,:].mean(axis=1)
    diff3sum = last3sum - prev3sum
    diff3avg =  last3avg - prev3avg
    diff3sum.name = 'L3vP3 $'
    diff3avg.name = 'L3vP3 $'
    final_df.loc[ind_sum,'L3vP3 $'] = diff3sum
    final_df.loc[ind_avg,'L3vP3 $'] = diff3avg

    try: d3sum_perc = diff3sum / prev3sum
    except: d3sum_perc = 0
    try: d3avg_perc = diff3avg / prev3avg
    except: d3avg_perc = 0
    d3sum_perc.name = 'L3vP3 %'
    d3avg_perc.name = 'L3vP3 %'
    final_df.loc[ind_sum,'L3vP3 %'] = d3sum_perc
    final_df.loc[ind_avg,'L3vP3 %'] = d3avg_perc

    # st.write(d3sum_perc, d3avg_perc)

    # ind_sum = [(11, 'Revenue'),    (12, 'Gross Profit'), (25, '4-Wall EBITDA'), 
    #            (26, '4-Wall FCF'), (27, 'Net Profit'),   (71, '# of Cars Serviced')    ]
    # ind_avg = [( 1, 'CPD'),            ( 2, 'ARO'),              (21, 'Labor %'),
    #             (22, 'Controllable %'),(23, 'Uncontrollable %'), (31, 'Cash'),
    #             (41, 'Gross Profit %'),(42, '4-Wall EBITDA %'),  (43, '4-Wall FCF %'),
    #             (44, 'Net Profit %'),  (51, 'LHPC'),             (52, 'Revenue Per Employee Hours Worked'),
    #             (61, 'P-Mix %'),       (62, 'Big 5 %'),          (63, 'Bay Times'),
    #             (64, 'Discount %'),    (72, 'Gross Profit Per Car'), (73, '4-Wall EBITDA Per Car')]

    # ind_dollar = [( 2, 'ARO')] #, 
    # ind_dollar = [(11, 'Revenue'), (12, 'Gross Profit'),(25, '4-Wall EBITDA'), 
    #             (26, '4-Wall FCF'), (27, 'Net Profit'),(31, 'Cash'),
    #             (52, 'Revenue Per Employee Hours Worked'),(72, 'Gross Profit Per Car'), 
    #             (73, '4-Wall EBITDA Per Car')]
    # for ind in ind_dollar:
    #     final_df.loc[ind, :] = final_df.loc[ind, :].apply(lambda x: f'${x:,.0f}')
    # final_df.loc[( 2, 'ARO'), :] = final_df.loc[( 2, 'ARO'), :].apply(lambda x: f'${x:,.0f}')
    final_df.loc[(11, 'Revenue'), :] = final_df.loc[(11, 'Revenue'), :].apply(lambda x: f'${x:,.0f}')
    final_df.loc[(12, 'Gross Profit'), :] = final_df.loc[(12, 'Gross Profit'), :].apply(lambda x: f'${x:,.0f}')


    return(final_df)



def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if hmac.compare_digest(st.session_state["password"], st.secrets["pagepassword"]):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the password.
        else:
            st.session_state["password_correct"] = False

    # Return True if the password is validated.
    if st.session_state.get("password_correct", False):
        return True

    # Show input for password.
    st.text_input(
        "Password", type="password", on_change=password_entered, key="password"
    )
    if "password_correct" in st.session_state:
        st.error("😕 Password incorrect")
    return False


# # Set the timeout period (in seconds)
# TIMEOUT = 60 * 5  # 5 minutes

# # Function to check if the user is authenticated
# def is_authenticated():
#     if 'authenticated' not in st.session_state or not st.session_state.authenticated:
#         return False
#     if 'timestamp' not in st.session_state:
#         return False
#     current_time = time.time()
#     if current_time - st.session_state.timestamp > TIMEOUT:
#         st.session_state.authenticated = False
#         return False
#     return True

# # Function to handle the authentication
# def authenticate(password_input):
#     correct_password = st.secrets["pagepassword"] #"your_password"  # Replace with your actual password
#     if password_input == correct_password:
#         st.session_state.authenticated = True
#         st.session_state.timestamp = time.time()
#     else:
#         st.session_state.authenticated = False
#         st.error("Incorrect password")

# # Main app logic
# if 'authenticated' not in st.session_state:
#     st.session_state.authenticated = False

# if is_authenticated():
#     st.success("You are authenticated!")
#     st.write("Your secured content goes here...")
# else:
#     st.warning("Please enter the password to access the content.")
#     password_input = st.text_input("Password", type="password")
#     if st.button("Submit"):
#         authenticate(password_input)
