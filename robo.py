import streamlit as st
import pandas as pd
from twelvedata import TDClient
from ta.trend import SMAIndicator
from ta.momentum import RSIIndicator
from datetime import datetime

# =========================
# CRIA CLIENTE COM SEGURANÇA
# =========================
def criar_client():
    api_key = st.secrets.get("4b17399dcf214533abd7d72ea416f1df", None)

    if not api_key:
        raise Exception("❌ API_KEY não encontrada nos Secrets do Streamlit")

    return TDClient(api_key)


# =========================
# PEGAR DADOS
# =========================
def pegar_dados():
    try:
        td = criar_client()

        ts = td.time_series(
            symbol="EUR/USD",
            interval="5min",
            outputsize=200
        ).as_pandas()

        ts = ts[::-1].reset_index(drop=True)

        for col in ['open', 'high', 'low', 'close']:
            ts[col] = pd.to_numeric(ts[col], errors='coerce')

        return ts.dropna()

    except Exception as e:
        print("Erro API:", e)
        return None


# =========================
# ROBÔ PRINCIPAL
# =========================
def executar_robo():

    data = pegar_dados()

    if data is None:
        return "❌ Erro ao buscar dados da API"

    # indicadores
    data['MA9'] = SMAIndicator(data['close'], 9).sma_indicator()
    data['MA21'] = SMAIndicator(data['close'], 21).sma_indicator()
    data['RSI'] = RSIIndicator(data['close'], 14).rsi()

    preco = data['close'].iloc[-1]
    ma9 = data['MA9'].iloc[-1]
    ma21 = data['MA21'].iloc[-1]
    rsi = data['RSI'].iloc[-1]

    horario = datetime.now().strftime("%H:%M:%S")

    # lógica simples
    sinal = "AGUARDAR"

    if rsi > 55 and ma9 > ma21:
        sinal = "COMPRA"
    elif rsi < 45 and ma9 < ma21:
        sinal = "VENDA"

    # saída do robô
    mensagem = f"""
📊 ROBÔ FOREX IA
💰 Preço: {preco}
📈 RSI: {rsi:.2f}
📉 MA9: {ma9:.5f}
📉 MA21: {ma21:.5f}

📌 Sinal: {sinal}
🕒 Hora: {horario}
"""

    return mensagem
