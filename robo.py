import streamlit as st
import pandas as pd
from twelvedata import TDClient
from ta.trend import SMAIndicator
from ta.momentum import RSIIndicator
from datetime import datetime

# =========================
# CLIENTE SEGURA API
# =========================
def criar_client():
    api_key = st.secrets.get("4b17399dcf214533abd7d72ea416f1df")

    if not api_key:
        raise Exception("API_KEY não encontrada nos Secrets")

    return TDClient(api_key)


# =========================
# PEGAR DADOS
# =========================
def pegar_dados():
    try:
        td = criar_client()

        ts = td.time_series(
            symbol="EUR/USD",   # 🔥 IMPORTANTE: formato correto
            interval="5min",
            outputsize=200
        ).as_pandas()

        ts = ts[::-1].reset_index(drop=True)

        for col in ["open", "high", "low", "close"]:
            ts[col] = pd.to_numeric(ts[col], errors="coerce")

        return ts.dropna()

    except Exception as e:
        print("Erro API:", e)
        return None


# =========================
# LÓGICA DO ROBÔ
# =========================
def executar_robo():

    data = pegar_dados()

    if data is None:
        return "❌ Erro ao buscar dados da API"

    # indicadores
    data["MA9"] = SMAIndicator(data["close"], 9).sma_indicator()
    data["MA21"] = SMAIndicator(data["close"], 21).sma_indicator()
    data["RSI"] = RSIIndicator(data["close"], 14).rsi()

    preco = data["close"].iloc[-1]
    ma9 = data["MA9"].iloc[-1]
    ma21 = data["MA21"].iloc[-1]
