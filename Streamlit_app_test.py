import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")

st.title('Olympic Games Medals')

route = 'http://winterolympicsmedals.com/medals.csv'

@st.cache
def load_data(nrows):
    df = pd.read_csv(route, nrows=nrows)
    return df

#data_load_state = st.text('Loading data...')
df = load_data(500000)
#data_load_state.text('Done! (using st.cache)')

option = st.selectbox(
     'Select a Gender',
     ('M','W','X'))

df = df[df['Event gender'] == option]
df