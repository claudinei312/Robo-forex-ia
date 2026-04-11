import streamlit as st
from streamlit_autorefresh import st_autorefresh
from robo import executar_robo

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Robô Forex IA", layout="centered")

st.title("🤖 Robô Forex Inteligente (Estável)")

# =========================
# AUTO REFRESH (60s)
# =========================
st_autorefresh(interval=60000, key="refresh")

# =========================
# EXECUÇÃO SEGURA
# =========================
try:
    resultado = executar_robo()

    if resultado:
        st.success("🟢 Robô ativo")
        st.text(resultado)
    else:
        st.warning("⚠️ Sem dados no momento")

except Exception as e:
    st.error("❌ Erro no robô")
    st.exception(e)
