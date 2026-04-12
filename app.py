import streamlit as st
import pandas as pd
from twelvedata import TDClient
from ta.trend import SMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange
from datetime import datetime, timedelta
import random

# =========================
# 🟩 CAMADA 1 - CONFIG
# =========================
st.set_page_config(page_title="🤖 Robô IA v9 FULL", layout="centered")
st.title("🤖 ROBÔ FOREX IA v9 - COMPLETO")

ligado = st.toggle("🔌 Ligar Robô", value=True)
ativo = st.selectbox("📊 Ativo", ["EUR/USD", "GBP/USD"])

td = TDClient(st.secrets["API_KEY"])

# =========================
# 🟦 CAMADA 3 - DADOS
# =========================
def pegar_dados():
    try:
        df = td.time_series(symbol=ativo, interval="5min", outputsize=500).as_pandas()
        df = df[::-1].reset_index(drop=True)

        for c in ["open", "high", "low", "close"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")

        return df.dropna()
    except:
        return None

# =========================
# 🟩 INDICADORES
# =========================
def indicadores(df):
    df["MA9"] = SMAIndicator(df["close"], 9).sma_indicator()
    df["MA21"] = SMAIndicator(df["close"], 21).sma_indicator()
    df["RSI"] = RSIIndicator(df["close"], 14).rsi()
    df["ATR"] = AverageTrueRange(df["high"], df["low"], df["close"], 14).average_true_range()
    return df

# =========================
# 🟨 ESTRATÉGIAS (SEM MEXER)
# =========================
def tendencia(df):
    rsi = df["RSI"].iloc[-1]
    if df["MA9"].iloc[-1] > df["MA21"].iloc[-1] and rsi > 55:
        return "COMPRA"
    if df["MA9"].iloc[-1] < df["MA21"].iloc[-1] and rsi < 45:
        return "VENDA"
    return "AGUARDAR"

def price_action(df):
    suporte = df["low"].rolling(20).min().iloc[-1]
    resistencia = df["high"].rolling(20).max().iloc[-1]
    preco = df["close"].iloc[-1]

    if preco <= suporte * 1.001:
        return "COMPRA"
    if preco >= resistencia * 0.999:
        return "VENDA"
    return "AGUARDAR"

def rejeicao(df):
    c = df.iloc[-1]
    corpo = abs(c["close"] - c["open"])

    if (c["open"] - c["low"]) > corpo * 2:
        return "COMPRA"
    if (c["high"] - c["open"]) > corpo * 2:
        return "VENDA"
    return "AGUARDAR"

def macd(df):
    m = MACD(df["close"])
    if m.macd().iloc[-1] > m.macd_signal().iloc[-1]:
        return "COMPRA"
    if m.macd().iloc[-1] < m.macd_signal().iloc[-1]:
        return "VENDA"
    return "AGUARDAR"

# =========================
# 🟫 BACKTEST ORIGINAL
# =========================
def backtest(df):
    wins = 0
    losses = 0

    for i in range(40, len(df)-1):

        sub = df.iloc[:i]
        estrategias = {
            "TENDENCIA": tendencia,
            "PRICE_ACTION": price_action,
            "REJEICAO": rejeicao,
            "MACD": macd
        }

        # usa tendência simples (igual seu robô)
        sinal = tendencia(sub)

        if sinal == "AGUARDAR":
            continue

        preco = sub["close"].iloc[-1]
        prox = df["close"].iloc[i+1]

        if (sinal == "COMPRA" and prox > preco) or (sinal == "VENDA" and prox < preco):
            wins += 1
        else:
            losses += 1

    total = wins + losses
    return wins, losses, (wins/total*100 if total else 0)

# =========================
# 📊 FILTRO DE DIAS ÚTEIS
# =========================
def filtrar_dias_uteis(df):
    return df  # API já vem sem calendário real de feriados, mantemos simples

# =========================
# 📊 BACKTEST SEMANA
# =========================
def backtest_semana():
    df = pegar_dados()
    if df is None:
        return None

    df = indicadores(df)
    df = filtrar_dias_uteis(df)

    return backtest(df)

# =========================
# 📊 BACKTEST DIA ANTERIOR
# =========================
def backtest_dia_anterior():
    df = pegar_dados()
    if df is None:
        return None

    df = indicadores(df)

    # simulação: pega últimos candles como "dia anterior"
    df = df.tail(100)

    return backtest(df)

# =========================
# 🟦 EXECUÇÃO
# =========================
if ligado:

    df = pegar_dados()

    if df is not None:

        df = indicadores(df)

        st.markdown("## 📊 BACKTEST CONTROLES")

        if st.button("📅 Backtest Última Semana"):
            w, l, wr = backtest_semana()
            st.success(f"Semana → Wins: {w} | Losses: {l} | Winrate: {wr:.2f}%")

        if st.button("📆 Backtest Dia Anterior"):
            w, l, wr = backtest_dia_anterior()
            st.info(f"Dia anterior → Wins: {w} | Losses: {l} | Winrate: {wr:.2f}%")

        st.markdown("---")

        # =========================
        # 📊 PAINEL NORMAL
        # =========================
        sinal = tendencia(df)
        preco = df["close"].iloc[-1]

        st.write("Ativo:", ativo)
        st.write("Preço:", preco)
        st.write("Sinal:", sinal)

else:
    st.warning("Robô desligado")
