from twelvedata import TDClient
import pandas as pd
from ta.trend import SMAIndicator
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange
from datetime import datetime
from ia_model import prever
from aprendizado import salvar_trade, analisar_erro
from email_service import enviar_email

API_KEY = "COLOCA_SUA_API_AQUI"

td = TDClient(API_KEY)

ativo = "EUR/USD"
intervalo = "5min"

def pegar_dados():
    ts = td.time_series(symbol=ativo, interval=intervalo, outputsize=200).as_pandas()
    ts = ts[::-1].reset_index(drop=True)
    for col in ['open','high','low','close']:
        ts[col] = pd.to_numeric(ts[col])
    return ts

def executar_robo():
    data = pegar_dados()

    data['MA9'] = SMAIndicator(data['close'], 9).sma_indicator()
    data['MA21'] = SMAIndicator(data['close'], 21).sma_indicator()
    data['RSI'] = RSIIndicator(data['close'], 14).rsi()

    preco = data['close'].iloc[-1]
    rsi = data['RSI'].iloc[-1]
    ma9 = data['MA9'].iloc[-1]
    ma21 = data['MA21'].iloc[-1]

    sinal = "AGUARDAR"

    if rsi > 55 and ma9 > ma21:
        sinal = "COMPRA"
    elif rsi < 45 and ma9 < ma21:
        sinal = "VENDA"

    ia = prever(rsi, ma9, ma21, preco)

    if sinal != "AGUARDAR" and ia == 1:
        msg = f"🚨 {sinal} {ativo} | Preço: {preco}"
        enviar_email(msg)
        salvar_trade(rsi, sinal)

        return f"✅ Entrada {sinal} com IA"

    return "⏳ Aguardando mercado"
