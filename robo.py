import streamlit as st
from twelvedata import TDClient
import pandas as pd

API_KEY = st.secrets["4b17399dcf214533abd7d72ea416f1df"]
td = TDClient(API_KEY)

ativo = "EUR/USD"
intervalo = "5min"


@st.cache_data(ttl=300)  # 🔥 ESSENCIAL
def pegar_dados():
    try:
        ts = td.time_series(
            symbol=ativo,
            interval=intervalo,
            outputsize=200
        ).as_pandas()

        ts = ts[::-1].reset_index(drop=True)

        for col in ['open', 'high', 'low', 'close']:
            ts[col] = pd.to_numeric(ts[col], errors='coerce')

        return ts.dropna()

    except Exception as e:
        print("Erro API:", e)
        return None
