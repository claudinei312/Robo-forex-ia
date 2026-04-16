# =========================
# IMPORTS
# =========================
import streamlit as st
import pandas as pd
from twelvedata import TDClient
from ta.trend import SMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange
from datetime import datetime
import requests


# =========================
# CONFIG STREAMLIT
# =========================
st.set_page_config(page_title="🤖 ROBÔ IA OTIMIZADO", layout="centered")
st.title("🤖 ROBÔ IA MULTI-ESTRATÉGIA (OTIMIZADO)")

ligado = st.toggle("🔌 Ligar Robô", value=True)

td = TDClient(st.secrets["API_KEY"])

ativos = ["EUR/USD", "USD/JPY", "AUD/USD"]


# =========================
# CACHE DADOS (EVITA TRAVAMENTO)
# =========================
@st.cache_data(ttl=60)
def pegar_dados(ativo):
    try:
        df = td.time_series(
            symbol=ativo,
            interval="5min",
            outputsize=300
        ).as_pandas()

        df = df[::-1].reset_index(drop=True)

        for c in ["open", "high", "low", "close"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")

        return df.dropna()
    except:
        return None


# =========================
# INDICADORES
# =========================
def indicadores(df):
    df["MA9"] = SMAIndicator(df["close"], 9).sma_indicator()
    df["MA21"] = SMAIndicator(df["close"], 21).sma_indicator()
    df["RSI"] = RSIIndicator(df["close"], 14).rsi()
    df["ATR"] = AverageTrueRange(df["high"], df["low"], df["close"], 14).average_true_range()
    return df


# =========================
# IA - ESCOLHA DE ESTRATÉGIA
# =========================
def escolher_estrategia(df):

    ma9 = df["MA9"].iloc[-1]
    ma21 = df["MA21"].iloc[-1]
    rsi = df["RSI"].iloc[-1]
    atr = df["ATR"].iloc[-1]
    price = df["close"].iloc[-1]

    tendencia = abs(ma9 - ma21)
    volatilidade = atr / price

    if tendencia > atr * 0.5:
        return "TREND"

    if 40 < rsi < 60:
        return "REVERSAO"

    if volatilidade > 0.003:
        return "BREAKOUT"

    return "TREND"


# =========================
# ESTRATÉGIAS
# =========================
def estrategia_trend(df):

    if df["MA9"].iloc[-1] > df["MA21"].iloc[-1]:
        return "COMPRA"
    if df["MA9"].iloc[-1] < df["MA21"].iloc[-1]:
        return "VENDA"
    return "AGUARDAR"


def estrategia_reversao(df):

    rsi = df["RSI"].iloc[-1]

    if rsi < 30:
        return "COMPRA"
    if rsi > 70:
        return "VENDA"
    return "AGUARDAR"


def estrategia_breakout(df):

    atr = df["ATR"].iloc[-1]
    close = df["close"].iloc[-1]

    high_prev = df["high"].iloc[-2]
    low_prev = df["low"].iloc[-2]

    if close > high_prev + atr:
        return "COMPRA"
    if close < low_prev - atr:
        return "VENDA"

    return "AGUARDAR"


# =========================
# SINAL FINAL (IA)
# =========================
def sinal(df):

    modo = escolher_estrategia(df)

    if modo == "TREND":
        return estrategia_trend(df), modo

    if modo == "REVERSAO":
        return estrategia_reversao(df), modo

    if modo == "BREAKOUT":
        return estrategia_breakout(df), modo

    return "AGUARDAR", modo


# =========================
# BACKTEST REALISTA (SÓ MANUAL)
# =========================
def backtest_realista(df):

    wins = 0
    losses = 0

    sl_mult = 1.0
    tp_mult = 1.5
    max_bars = 20

    for i in range(60, len(df) - max_bars):

        sub = df.iloc[:i]
        sig, _ = sinal(sub)

        if sig == "AGUARDAR":
            continue

        entry = df["open"].iloc[i]
        atr = sub["ATR"].iloc[-1]

        sl = atr * sl_mult
        tp = atr * tp_mult

        result = None

        for j in range(i + 1, i + max_bars):

            high = df["high"].iloc[j]
            low = df["low"].iloc[j]

            if sig == "COMPRA":
                if low <= entry - sl:
                    result = -1
                    break
                if high >= entry + tp:
                    result = 1
                    break

            elif sig == "VENDA":
                if high >= entry + sl:
                    result = -1
                    break
                if low <= entry + tp:
                    result = 1
                    break

        if result == 1:
            wins += 1
        elif result == -1:
            losses += 1

    total = wins + losses
    wr = (wins / total * 100) if total > 0 else 0

    return wins, losses, total, round(wr, 2)


# =========================
# EXECUÇÃO PRINCIPAL
# =========================
if ligado:

    st.markdown("## 📊 PAINEL IA OTIMIZADO")

    ranking = {}

    for ativo in ativos:

        df = pegar_dados(ativo)
        if df is None:
            continue

        df = indicadores(df)

        sig, modo = sinal(df)
        preco = df["close"].iloc[-1]

        st.markdown(f"### {ativo}")
        st.write("💰 Preço:", preco)
        st.write("🧠 IA MODE:", modo)
        st.write("📌 Sinal:", sig)

        # BACKTEST SOMENTE SE USUÁRIO QUISER
        if st.button(f"Rodar Backtest {ativo}"):

            w, l, t, wr = backtest_realista(df)

            st.write(f"📊 Wins: {w}")
            st.write(f"📉 Losses: {l}")
            st.write(f"🎯 Winrate: {wr}%")

            ranking[ativo] = wr

    st.markdown("## 🏆 Ranking (quando rodar backtest)")
    st.write(ranking)

else:
    st.warning("Robô desligado")
