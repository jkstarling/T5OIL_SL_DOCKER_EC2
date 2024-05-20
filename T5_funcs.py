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
    # st.write('Ext.avg', ext_avg)
    # st.write('Ext.sum', ext_sum)
    # st.write(work_pivot)

    ### 1 CPD
    pivot_table.loc[(1, 'CPD'),:] = ext_sum.loc['CarsServ', :] / work_pivot.loc['workdays', :] 

    ### 11  Total Income	(sum all 4000s)
    summed_values = filter_add_accounts(pivot_table, 4000, 4999)
    pivot_table.loc[(11, 'Revenue'), :] = summed_values

     ### 2 ARO
    pivot_table.loc[(2, 'ARO'),:] = pivot_table.loc[(11, 'Revenue'), :] / ext_sum.loc['CarsServ', :]

    ### 5998 Total Cost of Goods Sold	(sum all 5000s)
    summed_values = filter_add_accounts(pivot_table, 5000, 5998)
    pivot_table.loc[(5998, 'Total Cost of Goods Sold'), :] = summed_values
    ###  12  Gross Profit	5998  minus 11
    top = pivot_table.loc[(11, 'Revenue'), :]
    bot = pivot_table.loc[(5998, 'Total Cost of Goods Sold'), :]
    pivot_table.loc[(12, 'Gross Profit'), :] = top - bot

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
    pivot_table.loc[(9990, 'Net Other Income'), :] = top - bot

    ###  27   Net Income	           9990 plus 8999
    top = pivot_table.loc[(9990, 'Net Other Income'), :]
    bot = pivot_table.loc[(8999, 'Net Operating Income'), :]
    pivot_table.loc[(27, 'Net Profit'), :] = top + bot

    # remove all 0.0s and replace with NaNs
    pivot_table.replace(0.0, np.nan, inplace=True)


    ##### create 4 wall reports #####

    # 10005	4 Wall Expenses	(all 6000 to 7999)
    summed_values = filter_add_accounts(pivot_table, 6000, 7999)
    pivot_table.loc[(10005, '4 Wall Expenses'), :] = summed_values

    # 25	4 Wall Profit	Gross Profit 5999 minus 10005
    top = pivot_table.loc[(12, 'Gross Profit'), :]
    bot = pivot_table.loc[(10005, '4 Wall Expenses'), :]
    pivot_table.loc[(25, '4-Wall EBITDA'), :] = top - bot

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
    pivot_table.loc[(21, 'Labor %'), :] = top / bot

    # 22	Controllable %	10012 divide by  11  (11, 'Revenue')
    top = pivot_table.loc[(10012, 'Controllable'), :]
    bot = pivot_table.loc[(11, 'Revenue'), :]
    pivot_table.loc[(22, 'Controllable %'), :] = top / bot

    # 23	Uncontrollable %	10013 divide by  11  (11, 'Revenue')
    top = pivot_table.loc[(10013, 'Uncontrollable'), :]
    bot = pivot_table.loc[(11, 'Revenue'), :]
    pivot_table.loc[(23, 'Uncontrollable %'), :] = top / bot

    #26 4-Wall FCF
    top = pivot_table.loc[(8999, 'Net Operating Income'),:]
    bot = pivot_table.loc[(9230, '9230 Interest Expense'),:]
    pivot_table.loc[(26, '4-Wall FCF'), :] = top / bot

    #31 Cash
    summed_values = filter_add_accounts(pivot_table, 1000, 1099)
    pivot_table.loc[(31, 'Cash'), :] = summed_values

    #41 Gross Profit %
    top = pivot_table.loc[(12, 'Gross Profit'),:]
    bot = pivot_table.loc[(11, 'Revenue'),:]
    pivot_table.loc[(41, 'Gross Profit %'), :] = top / bot

    #42 4-WALL EBITDA %
    top = pivot_table.loc[(25, '4-Wall EBITDA'),:]
    bot = pivot_table.loc[(11, 'Revenue'),:]
    pivot_table.loc[(42, '4-Wall EBITDA %'), :] = top / bot

    #43 4-WALL FCF %
    top = pivot_table.loc[(26, '4-Wall FCF'),:]
    bot = pivot_table.loc[(11, 'Revenue'),:]
    pivot_table.loc[(43, '4-Wall FCF %'), :] = top / bot

    #44 4-WALL FCF %
    top = pivot_table.loc[(27, 'Net Profit'),:]
    bot = pivot_table.loc[(11, 'Revenue'),:]
    pivot_table.loc[(44, 'Net Profit %'), :] = top / bot

    #51 LHPC
    pivot_table.loc[(51, 'LHPC'),:] = ext_sum.loc['CarsServ', :] / ext_sum.loc['EmpHours', :]
    #52 Revenue Per Employee Hours Worked
    pivot_table.loc[(52, 'Revenue Per Employee Hours Worked'),:] = pivot_table.loc[(11, 'Revenue'), :] / ext_sum.loc['EmpHours', :]

    #61 P-Mix %
    pivot_table.loc[(61, 'P-Mix %'),:] = ext_avg.loc['Pmix_perc', :]
    #62 Big 5 %
    pivot_table.loc[(62, 'Big 5 %'),:] = ext_avg.loc['Big5_perc', :]
    #63 Bay Times
    pivot_table.loc[(63, 'Bay Times'),:] = ext_avg.loc['BayTimes', :]
    #64 Discount %
    summed_values = filter_add_accounts(pivot_table, 4099, 4899)
    pivot_table.loc[(64, 'Discount %'),:] = pivot_table.loc[(4900, '4900 Sales - Discounts'), :] / summed_values 
    
    #71 # of Cars Serviced
    pivot_table.loc[(71, '# of Cars Serviced'),:] = ext_sum.loc['CarsServ', :]
    #72 Gross Profit Per Car
    pivot_table.loc[(72, 'Gross Profit Per Car'),:] = pivot_table.loc[(12, 'Gross Profit'), :] / ext_sum.loc['CarsServ', :]
    #73 4-Wall EBITDA Per Car
    pivot_table.loc[(73, '4-Wall EBITDA Per Car'),:] = pivot_table.loc[(25, '4-Wall EBITDA'), :] / ext_sum.loc['CarsServ', :]
    
    # make blank rows
    for i in [10, 20, 24, 30, 40, 50, 60, 70]:
        pivot_table.loc[(i, ''), :] = [None] * len(pivot_table.columns)

    final_df = pivot_table.loc[pivot_table.index.get_level_values(0) < 100] 
    # Sort the index
    final_df.sort_index(inplace=True)

    return(final_df)

