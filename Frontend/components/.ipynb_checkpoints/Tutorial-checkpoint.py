import streamlit as st


# Temporary Introduction page showing a Hello World message
def show_tutorials_page():
    
    st.set_page_config(page_title="Introduction", layout="centered")
    st.title("Hello World")
    st.write("This is the temporary Introduction page.")