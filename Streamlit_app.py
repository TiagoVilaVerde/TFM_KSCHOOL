import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")

st.title('Top European Football National Leagues Predictions')

route = '/Users/tiago/Master/0. TFM/TFM_Github/Predictions.xlsx'

@st.cache
def load_data(nrows):
    df = pd.read_excel(route, nrows=nrows)
    df = df.drop(['Unnamed: 0'], axis=1)
    return df

#data_load_state = st.text('Loading data...')
df = load_data(500000)
#data_load_state.text('Done! (using st.cache)')

option = st.selectbox(
     'Select a National League',
     ('Portugal','Spain','England','Italy','Germany','France'))

df = df[df['Country'] == option]
df