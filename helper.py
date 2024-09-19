# Import Function Modules
import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def arrow_form_perc(val):
    epsilon = 0.001
    if val > -epsilon and val < epsilon:
        return '  (0%)'
    elif val > 0:
        return f':green[ (↑ {val:.2f}%)]'
    elif val < 0:
        return f':red[ (↓ {abs(val):.2f}%)]'
    else:
        return '  (No data)' 

def arrow_form_perc_opp(val):
    epsilon = 0.001
    if val > -epsilon and val < epsilon:
        return '  (0%)'
    elif val > 0:
        return f':red[ (↑ {val:.2f}%)]'
    elif val < 0:
        return f':green[ (↓ {abs(val):.2f}%)]'
    else:
        return '  (No data)' 

def arrow_form_num(val):
    epsilon = 0.001
    if val > -epsilon and val < epsilon:
        return '  (0)'
    elif val > 0:
        return f':green[ (↑ {val:.2f})]'
    elif val < 0:
        return f':red[ (↓ {abs(val):.2f})]'
    else:
        return '  (No data)' 

def arrow_form_num_opp(val):
    epsilon = 0.001
    if val > -epsilon and val < epsilon:
        return '  (0)'
    elif val < 0:
        return f':green[ (↓ {val:.2f})]'
    elif val > 0:
        return f':red[ (↑ {abs(val):.2f})]'
    else:
        return ' (No data)' 

def pmix_form(val):
    val = val * 100
    if val >= 90:
        return f':green[{val:.0f}%]'
    else:
        return f':red[{val:.0f}%]'

def big5_form(val):
    val = val * 100
    if val >= 50:
        return f':green[{val:.0f}%]'
    else:
        return f':red[{val:.0f}%]'

def baytime_form(val):
    if val <= 10:
        return f':green[{val:.0f}]'
    else:
        return f':red[{val:.0f}]'

def kdollar_form(val):
    return f'${val:,.2f}K'

def dollar_form(val):
    return f'${val:,.0f}'

def perc_form(val):
    return f'{val:.2f}%'

def numb_form(val):
    return f'{int(val):,}'

def format_two_decimals(x):
    return f"{x:.2f}"

def perc_print(mymetric, mynumb, myperc):
    st.write(mymetric + arrow_form(myperc))    
    st.markdown(f"""<p style='font-size:30px;'>{perc_form(mynumb)}</p>""", unsafe_allow_html=True)

def numb_print(mymetric, mynumb, myperc):
    st.write(mymetric + arrow_form(myperc))
    st.markdown(f"""<p style='font-size:30px;'>{numb_form(mynumb)}</p>""", unsafe_allow_html=True)

def kdollar_print(mymetric, mynumb, myperc):
    st.write(mymetric + arrow_form(myperc))
    st.markdown(f"<p style='font-size:30px;'>{kdollar_form(mynumb)}</p>", unsafe_allow_html=True)

def dollar_print(mymetric, mynumb, myperc):
    st.write(mymetric + arrow_form(myperc))
    st.markdown(f"<p style='font-size:30px;'>{dollar_form(mynumb)}</p>", unsafe_allow_html=True)

def gauge_font(mytext):
    print(f"<p style='font-size:30px;'>{mytext}</p>", unsafe_allow_html=True)
    # st.markdown(f"<p style='font-size:30px;'>{mytext}</p>", unsafe_allow_html=True)
