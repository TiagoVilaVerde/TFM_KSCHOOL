import streamlit as st
import pandas as pd

CURRENT_THEME = "blue"
IS_DARK_THEME = True
EXPANDER_TEXT = """
    This is a custom theme. You can enable it by copying the following code
    to `.streamlit/config.toml`:
    ```python
    [theme]
    primaryColor = "#E694FF"
    backgroundColor = "#00172B"
    secondaryBackgroundColor = "#0083B8"
    textColor = "#C6CDD4"
    font = "sans-serif"
    ```
    """

st.set_page_config(layout="wide")

st.title('Top European Football National Leagues Predictions')

df = pd.read_csv('https://storage.googleapis.com/tiago-tfm-kschool/Table_final_user.csv')

last_update_date = list(df['Last update date'])[0]

st.write('Last udpate date:', last_update_date)

option_country = st.selectbox(
     'Select a National League',
     ('Portugal','Spain','England','Italy','Germany','France'))

option_weekday = st.selectbox(
     'Select weekday',
     ('Current','Following'))

df = df[(df['Country'] == option_country) &\
    (df['Weekday'] == option_weekday)]

df.drop(['Country', 'Weekday', 'Last update date'],axis = 1, inplace = True)

# To hide index:
# CSS to inject contained in a string
hide_table_row_index = """
            <style>
            tbody th {display:none}
            .blank {display:none}
            </style>
            """

# Inject CSS with Markdown
st.markdown(hide_table_row_index, unsafe_allow_html=True)

# Display a static table
st.table(df)

# Display an image
st.image('https://storage.googleapis.com/tiago-tfm-kschool/Football_Stadium.jpg',caption='Image from unsplash.com')
