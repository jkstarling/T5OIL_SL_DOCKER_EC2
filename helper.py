# Import Function Modules
import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def arrow_format(val):
    if val > 0:
        return f':green[ (↑ {val:.1f}%)]'
    elif val < 0:
        return f':red[ (↓ {abs(val):.1f}%)]'
    elif val == np.nan():
        return f'No data'
    else:
        return f' ({val:.0}%)'

def kdollar_format(val):
    return f'${val:,.2f}K'

def dollar_format(val):
    return f'${val:,.2f}'

def perc_format(val):
    return f'{val:.2f}%'

def numb_format(val):
    return f'{int(val):,}'

def format_two_decimals(x):
    return f"{x:.2f}"

def perc_print(mymetric, mynumb, myperc):
    st.write(mymetric + arrow_format(myperc))    
    st.markdown(f"""<p style='font-size:30px;'>{perc_format(mynumb)}</p>""", unsafe_allow_html=True)

def numb_print(mymetric, mynumb, myperc):
    st.write(mymetric + arrow_format(myperc))
    st.markdown(f"""<p style='font-size:30px;'>{numb_format(mynumb)}</p>""", unsafe_allow_html=True)

def kdollar_print(mymetric, mynumb, myperc):
    st.write(mymetric + arrow_format(myperc))
    st.markdown(f"<p style='font-size:30px;'>{kdollar_format(mynumb)}</p>", unsafe_allow_html=True)

def dollar_print(mymetric, mynumb, myperc):
    st.write(mymetric + arrow_format(myperc))
    st.markdown(f"<p style='font-size:30px;'>{dollar_format(mynumb)}</p>", unsafe_allow_html=True)
