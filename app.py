import streamlit as st
import pandas as pd
from twelvedata import TDClient
from ta.trend import SMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange
from datetime import datetime
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
# 🟦 CAMADA 3 - DADOS (AJUSTADO PARA 70%)
# =========================
def pegar_dados():
    try:
        df = td.time_series(
            symbol=ativo,
            interval="15min",
            outputsize=5000
        ).as_pandas()

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
# 🧠 ESTRATÉGIA IA (70% BASE - NÃO MEXER)
# =========================
def score_ia(df):

    score = 0

    if df["MA9"].iloc[-1] > df["MA21"].iloc[-1]:
        score += 1
    else:
        score -= 1

    rsi = df["RSI"].iloc[-1]
    if rsi > 55:
        score += 1
    elif rsi < 45:
        score -= 1

    m = MACD(df["close"])
    if m.macd().iloc[-1] > m.macd_signal().iloc[-1]:
        score += 1
    else:
        score -= 1

    atr = df["ATR"].iloc[-1]
    if atr > df["ATR"].rolling(50).mean().iloc[-1]:
        score += 1
    else:
        score -= 1

    return score


def tendencia_forte(df):

    closes = df["close"].tail(10)

    alta = 0
    baixa = 0

    for i in range(1, len(closes)):
        if closes.iloc[i] > closes.iloc[i-1]:
            alta += 1
        else:
            baixa += 1

    if alta >= 8:
        return "UP"

    if baixa >= 8:
        return "DOWN"

    return "LATERAL"


def filtro_distancia(df):

    price = df["close"].iloc[-1]
    ma21 = df["MA21"].iloc[-1]
    atr = df["ATR"].iloc[-1]

    distancia = abs(price - ma21)

    if distancia > atr * 1.8:
        return False

    return True


def entrada_extra(df):

    price = df["close"].iloc[-1]
    ma21 = df["MA21"].iloc[-1]
    atr = df["ATR"].iloc[-1]

    score = score_ia(df)
    trend = tendencia_forte(df)

    pullback = abs(price - ma21) < atr * 0.9

    last = df["close"].iloc[-1]
    prev = df["close"].iloc[-2]

    micro_up = last > prev
    micro_down = last < prev

    if trend == "UP" and score >= 2 and pullback and micro_up:
        return "COMPRA"

    if trend == "DOWN" and score <= -2 and pullback and micro_down:
        return "VENDA"

    return "AGUARDAR"


def sinal(df):

    score = score_ia(df)
    trend = tendencia_forte(df)

    if trend == "LATERAL":
        return "AGUARDAR"

    if not filtro_distancia(df):
        return "AGUARDAR"

    if trend == "UP" and score < 2:
        core_signal = "AGUARDAR"
    elif trend == "DOWN" and score > -2:
        core_signal = "AGUARDAR"
    elif score >= 3 and trend == "UP":
        core_signal = "COMPRA"
    elif score <= -3 and trend == "DOWN":
        core_signal = "VENDA"
    else:
        core_signal = "AGUARDAR"

    if core_signal == "AGUARDAR":
        return entrada_extra(df)

    return core_signal

# =========================
# 🟨 HORÁRIO
# =========================
def horario_sistema():
    hora = datetime.now().hour
    dia = datetime.now().weekday()

    return {
        "operacao_liberada": hora >= 8,
        "fim_de_semana": dia >= 5
    }

# =========================
# 🧠 BACKTEST (CORRIGIDO 70%)
# =========================
def backtest(df):

    wins = 0
    losses = 0

    for i in range(60, len(df) - 1):

        sub = df.iloc[:i]
        sig = sinal(sub)

        if sig == "AGUARDAR":
            continue

        price = sub["close"].iloc[-1]
        next_price = df["close"].iloc[i + 1]

        if (sig == "COMPRA" and next_price > price) or (sig == "VENDA" and next_price < price):
            wins += 1
        else:
            losses += 1

    total = wins + losses
    return wins, losses, (wins / total * 100 if total else 0)

# =========================
# 🟦 EXECUÇÃO
# =========================
if ligado:

    df = pegar_dados()

    if df is not None:

        df = indicadores(df)

        status = horario_sistema()

        sinal_atual = sinal(df)
        preco = df["close"].iloc[-1]

        if not status["operacao_liberada"]:
            sinal_atual = "AGUARDAR"

        st.markdown("## 📊 PAINEL IA")

        st.write("Ativo:", ativo)
        st.write("Preço:", preco)
        st.write("Sinal:", sinal_atual)

        atr = df["ATR"].iloc[-1]

        if "posicao" not in st.session_state:
            st.session_state.posicao = None

        if sinal_atual != "AGUARDAR" and st.session_state.posicao is None:

            st.session_state.posicao = {
                "tipo": sinal_atual,
                "entrada": preco,
                "tp": preco + atr*2 if sinal_atual == "COMPRA" else preco - atr*2,
                "sl": preco - atr if sinal_atual == "COMPRA" else preco + atr
            }

        st.markdown("## 📌 OPERAÇÃO")
        st.write(st.session_state.posicao)

        # BACKTEST
        w, l, wr = backtest(df)

        st.markdown("## 📊 BACKTEST")
        st.write(w, l, wr)

else:
    st.warning("Robô desligado")
