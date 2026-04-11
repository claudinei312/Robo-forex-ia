import streamlit as st
import pandas as pd
from twelvedata import TDClient
from ta.trend import SMAIndicator
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh
import smtplib
from email.mime.text import MIMEText

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="IA Forex Pro", layout="centered")

ativo = "EUR/USD"
st.title(f"🤖 IA Forex Pro - {ativo}")

st_autorefresh(interval=60000, key="refresh")

ligado = st.toggle("🔌 Ligar Robô", value=True)

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

if "posicao" not in st.session_state:
    st.session_state.posicao = None

if "model_bias" not in st.session_state:
    st.session_state.model_bias = 1.0

# =========================
# EMAIL
# =========================
def enviar_email(msg):
    try:
        m = MIMEText(msg)
        m["Subject"] = "🤖 ROBÔ IA ALERTA"
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
# SCORE IA
# =========================
def score(df):

    df["MA9"] = SMAIndicator(df["close"], 9).sma_indicator()
    df["MA21"] = SMAIndicator(df["close"], 21).sma_indicator()
    df["RSI"] = RSIIndicator(df["close"], 14).rsi()

    preco = df["close"].iloc[-1]
    ma9 = df["MA9"].iloc[-1]
    ma21 = df["MA21"].iloc[-1]
    rsi = df["RSI"].iloc[-1]

    s = 50

    if ma9 > ma21:
        s += 20
    else:
        s -= 20

    if rsi > 55:
        s += 15
    elif rsi < 45:
        s -= 15

    s *= st.session_state.model_bias

    return max(0, min(100, s)), preco

# =========================
# DECISÃO
# =========================
def sinal(score):

    if score >= 72:
        return "COMPRA"
    if score <= 28:
        return "VENDA"
    return "AGUARDAR"

# =========================
# BACKTEST EM TEMPO REAL
# =========================
def atualizar_backtest(preco_atual):

    pos = st.session_state.posicao

    if pos is None:
        return

    tipo = pos["tipo"]
    entrada = pos["entrada"]

    resultado = None

    if tipo == "COMPRA":

        if preco_atual >= entrada * 1.0005:
            resultado = "WIN"
        elif preco_atual <= entrada * 0.9995:
            resultado = "LOSS"

    if tipo == "VENDA":

        if preco_atual <= entrada * 0.9995:
            resultado = "WIN"
        elif preco_atual >= entrada * 1.0005:
            resultado = "LOSS"

    if resultado:

        st.session_state.trades.append(resultado)
        st.session_state.posicao = None

# =========================
# STATS
# =========================
def stats():

    wins = len([t for t in st.session_state.trades if t == "WIN"])
    losses = len([t for t in st.session_state.trades if t == "LOSS"])

    total = wins + losses

    if total == 0:
        return 50, wins, losses

    return (wins / total) * 100, wins, losses

# =========================
# RUN
# =========================
if ligado:

    df = dados()

    sc, preco = score(df)

    sig = sinal(sc)

    # =========================
    # BACKTEST REAL
    # =========================
    atualizar_backtest(preco)

    winrate, wins, losses = stats()

    # =========================
    # ENTRADA
    # =========================
    if sig != "AGUARDAR" and st.session_state.posicao is None:

        st.session_state.posicao = {
            "tipo": sig,
            "entrada": preco
        }

        enviar_email(f"{sig} {ativo} {preco}")

    # =========================
    # PAINEL
    # =========================
    st.markdown("## 📊 IA Trading Panel")

    st.write(f"💱 Ativo: {ativo}")
    st.write(f"💰 Preço: {preco}")
    st.write(f"🧠 Score: {round(sc,2)}")

    st.write(f"📊 Winrate: {round(winrate,2)}%")
    st.write(f"📈 Wins: {wins} | ❌ Losses: {losses}")

    if st.session_state.posicao:
        st.warning(f"📌 Em operação: {st.session_state.posicao}")

    else:
        st.info("⏳ Sem operação ativa")

else:
    st.warning("Robô desligado")
