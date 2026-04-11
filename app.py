import streamlit as st
from streamlit_autorefresh import st_autorefresh
from robo import executar_robo

# =========================
# CONFIGURAÇÃO
# =========================
st.set_page_config(page_title="Robô Forex IA", layout="centered")

st.title("🤖 Robô Forex Inteligente")

# =========================
# AUTO REFRESH (60s)
# =========================
st_autorefresh(interval=60000, key="refresh")

# =========================
# EXECUÇÃO
# =========================
try:
    resultado = executar_robo()

    st.success("🟢 Robô rodando normalmente")
    st.text(resultado)

except Exception as e:
    st.error("❌ Erro no robô")
    st.exception(e)
