import streamlit as st
from streamlit_autorefresh import st_autorefresh
from robo import executar_robo

st.set_page_config(page_title="Robô Forex IA")

st.title("🤖 Robô Forex Inteligente")

# Atualiza a cada 5 minutos
st_autorefresh(interval=300000)

resultado = executar_robo()

st.write(resultado)
