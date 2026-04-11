import streamlit as st
from twelvedata import TDClient
import pandas as pd
from ta.trend import SMAIndicator
from ta.momentum import RSIIndicator
from datetime import datetime

from ia_model import prever
from email_service import enviar_email
from aprendizado import salvar_trade, analisar_erro

# 🔐 API segura (Streamlit Secrets)
API_KEY = st.secrets["4b17399dcf214533abd7d72ea416f1df"]
td = TDClient(API_KEY)

ativo = "EUR/USD"
intervalo = "5min"


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
        return None


def executar_robo():

    data = pegar_dados()

    if data is None:
        return "⚠️ Erro ao buscar dados da API"

    # indicadores
    data['MA9'] = SMAIndicator(data['close'], 9).sma_indicator()
    data['MA21'] = SMAIndicator(data['close'], 21).sma_indicator()
    data['RSI'] = RSIIndicator(data['close'], 14).rsi()

    preco = data['close'].iloc[-1]
    rsi = data['RSI'].iloc[-1]
    ma9 = data['MA9'].iloc[-1]
    ma21 = data['MA21'].iloc[-1]

    horario = datetime.now().strftime("%H:%M:%S")

    # estratégia base
    sinal = "AGUARDAR"

    if rsi > 55 and ma9 > ma21:
        sinal = "COMPRA"
    elif rsi < 45 and ma9 < ma21:
        sinal = "VENDA"

    # IA (filtro)
    decisao_ia = prever(rsi, ma9, ma21, preco)

    if sinal != "AGUARDAR" and decisao_ia == 1:

        msg = f"""
🚨 ENTRADA {ativo}
📊 {sinal}
💰 Preço: {preco}
🕒 {horario}
🤖 IA: APROVADO
"""

        enviar_email(msg)
        salvar_trade(rsi, sinal)

        return msg

    return f"⏳ Aguardando mercado... | RSI: {rsi:.2f}"
