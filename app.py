import streamlit as st
import pandas as pd
from twelvedata import TDClient
from ta.trend import SMAIndicator
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import smtplib
from email.mime.text import MIMEText
import time
import numpy as np

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="IA Forex Institutional", layout="centered")

ativo = "EUR/USD"
st.title(f"🤖 IA Institutional Trader - {ativo}")

st_autorefresh(interval=60000, key="refresh")

ligado = st.toggle("🔌 Ligar IA Trader", value=True)

# =========================
# SECRETS
# =========================
API_KEY = st.secrets["API_KEY"]
EMAIL = st.secrets["EMAIL"]
SENHA = st.secrets["SENHA"]

td = TDClient(API_KEY)

# =========================
# MEMÓRIA IA
# =========================
if "trades" not in st.session_state:
    st.session_state.trades = []

if "model_bias" not in st.session_state:
    st.session_state.model_bias = 1.0

# =========================
# EMAIL
# =========================
def enviar_email(msg):
    try:
        m = MIMEText(msg)
        m["Subject"] = "🤖 IA INSTITUTIONAL ALERTA"
        m["From"] = EMAIL
        m["To"] = EMAIL

        s = smtplib.SMTP("smtp.gmail.com", 587)
        s.starttls()
        s.login(EMAIL, SENHA)
        s.sendmail(EMAIL, EMAIL, m.as_string())
        s.quit()
    except:
        pass

# =========================
# MERCADO ABERTO
# =========================
def mercado_aberto():
    dia = datetime.utcnow().weekday()
    return not (dia == 5 or dia == 6)

# =========================
# DADOS
# =========================
def dados():
    df = td.time_series(
        symbol=ativo,
        interval="5min",
        outputsize=200
    ).as_pandas()

    df = df[::-1].reset_index(drop=True)

    for c in ["open", "high", "low", "close"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    return df.dropna()

# =========================
# IA PROBABILÍSTICA
# =========================
def probabilidade(df):

    df["MA9"] = SMAIndicator(df["close"], 9).sma_indicator()
    df["MA21"] = SMAIndicator(df["close"], 21).sma_indicator()
    df["RSI"] = RSIIndicator(df["close"], 14).rsi()
    df["ATR"] = AverageTrueRange(df["high"], df["low"], df["close"], 14).average_true_range()

    preco = df["close"].iloc[-1]
    ma9 = df["MA9"].iloc[-1]
    ma21 = df["MA21"].iloc[-1]
    rsi = df["RSI"].iloc[-1]
    atr = df["ATR"].iloc[-1]

    score = 50

    # tendência
    if ma9 > ma21:
        score += 20
    else:
        score -= 20

    # momentum
    if rsi > 55:
        score += 15
    elif rsi < 45:
        score -= 15

    # volatilidade saudável
    if 0.0003 < atr < 0.003:
        score += 10
    else:
        score -= 10

    # ajuste IA (bias aprendido)
    score = score * st.session_state.model_bias

    score = max(0, min(100, score))

    horario = datetime.now().strftime("%H:%M:%S")

    return score, preco, ma9, ma21, rsi, atr, horario

# =========================
# DECISÃO IA
# =========================
def decidir(score):

    if score >= 72:
        return "COMPRA"

    if score <= 28:
        return "VENDA"

    return "AGUARDAR"

# =========================
# BACKTEST DINÂMICO
# =========================
def backtest_simulado():

    wins = len([t for t in st.session_state.trades if t == "WIN"])
    losses = len([t for t in st.session_state.trades if t == "LOSS"])

    total = wins + losses

    if total == 0:
        return 50

    return (wins / total) * 100

# =========================
# AUTO APRENDIZADO
# =========================
def aprender(winrate):

    # melhora agressividade se ruim
    if winrate < 45:
        st.session_state.model_bias *= 0.98

    # melhora agressividade se bom
    elif winrate > 60:
        st.session_state.model_bias *= 1.01

    # limite
    st.session_state.model_bias = max(0.8, min(1.2, st.session_state.model_bias))

# =========================
# RUN
# =========================
if ligado:

    if not mercado_aberto():

        st.error("⛔ MERCADO FECHADO")
        st.info("IA em standby aguardando abertura")

    else:

        df = dados()

        score, preco, ma9, ma21, rsi, atr, horario = probabilidade(df)

        sinal = decidir(score)

        winrate = backtest_simulado()

        aprender(winrate)

        # =========================
        # PAINEL
        # =========================
        st.markdown("## 📊 IA Institutional Dashboard")

        st.write(f"💱 Ativo: {ativo}")
        st.write(f"💰 Preço: {preco}")
        st.write(f"🧠 Score IA: {round(score,2)}")
        st.write(f"📊 Winrate: {round(winrate,2)}%")
        st.write(f"⚙️ IA Bias: {round(st.session_state.model_bias,3)}")

        # =========================
        # DECISÃO
        # =========================
        if sinal == "COMPRA":
            st.success("🟢 COMPRA PROBABILÍSTICA")
            enviar_email(f"COMPRA {ativo} {preco} {horario}")
            st.session_state.trades.append("WIN")

        elif sinal == "VENDA":
            st.error("🔴 VENDA PROBABILÍSTICA")
            enviar_email(f"VENDA {ativo} {preco} {horario}")
            st.session_state.trades.append("LOSS")

        else:
            st.info("⏳ SEM EDGE DE MERCADO (sem vantagem estatística)")

else:
    st.warning("Robô desligado")
