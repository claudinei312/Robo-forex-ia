import streamlit as st
from streamlit_autorefresh import st_autorefresh
from robo import executar_robo

# =========================
# CONFIGURAÇÃO DA PÁGINA
# =========================
st.set_page_config(page_title="Robô Forex IA", layout="centered")

st.title("🤖 Robô Forex Inteligente (Modo Vela 5min)")

# =========================
# AUTO REFRESH (A CADA 60s)
# =========================
st_autorefresh(interval=60000, key="refresh")

# =========================
# EXECUTA ROBÔ
# =========================
try:
    resultado = executar_robo()
    st.success("🟢 Robô ativo - monitorando mercado")
    st.text(resultado)

except Exception as e:
    st.error("❌ Erro no robô")
    st.exception(e)
