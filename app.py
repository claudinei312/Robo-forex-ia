import streamlit as st
from streamlit_autorefresh import st_autorefresh
from robo import executar_robo

st.set_page_config(page_title="Robô Forex IA", layout="centered")

st.title("🤖 Robô Forex Inteligente com IA")

# atualiza a cada 5 min
st_autorefresh(interval=300000)

import streamlit as st
from streamlit_autorefresh import st_autorefresh
from robo import executar_robo

st.title("🤖 Robô Forex IA")

# atualiza a cada 5 minutos (SEGURADO)
st_autorefresh(interval=300000, key="refresh")

if st.button("Rodar análise agora"):
    resultado = executar_robo()
    st.write(resultado)
else:
    st.info("Clique no botão para rodar o robô")

st.write(resultado)
