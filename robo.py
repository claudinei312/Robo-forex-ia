import streamlit as st

API_KEY = st.secrets.get("API_KEY")

st.write("DEBUG API KEY:", API_KEY)
