import streamlit as st
st.title("Welcome to Streamlit!")
st.write("This is a simple Streamlit application.") 
prompt=st.chat_input("请输入你的内容 ")
if prompt:
    user_message=st.chat_message("human")
    user_message.write(prompt)

    ai_message=st.chat_message("ai")
    ai_message.write("这是AI的回复内容")
file_list=["文件1.csv", "文件2.txt", "文件3.txt"]
st.sidebar.selectbox("在当前目录下选择加载的文件", file_list)

import streamlit as st

st.title("Hello Streamlit-er 👋")
st.markdown(
    """ 
    This is a playground for you to try Streamlit and have fun. 

    **There's :rainbow[so much] you can build!**
    
    We prepared a few examples for you to get started. Just 
    click on the buttons above and discover what you can do 
    with Streamlit. 
    """
)

if st.button("Send balloons!"):
    st.balloons()

    
import pandas as pd
import numpy as np

st.write("Streamlit supports a wide range of data visualizations, including [Plotly, Altair, and Bokeh charts](https://docs.streamlit.io/develop/api-reference/charts). 📊 And with over 20 input widgets, you can easily make your data interactive!")

all_users = ["Alice", "Bob", "Charly"]
with st.container(border=True):
    users = st.multiselect("Users", all_users, default=all_users)
    rolling_average = st.toggle("Rolling average")

np.random.seed(42)
data = pd.DataFrame(np.random.randn(20, len(users)), columns=users)
if rolling_average:
    data = data.rolling(7).mean().dropna()

tab1, tab2 = st.tabs(["Chart", "Dataframe"])
tab1.line_chart(data, height=250)
tab2.dataframe(data, height=250, use_container_width=True)