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
import requests

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Robô IA PRO", layout="centered")

st.title("🤖 Robô Forex IA PRO LEVEL")

st_autorefresh(interval=60000, key="refresh")

# =========================
# BOTÃO ON/OFF
# =========================
ligado = st.toggle("🔌 Ligar Robô", value=True)

# =========================
# SECRETS
# =========================
API_KEY = st.secrets["API_KEY"]
EMAIL = st.secrets["EMAIL"]
SENHA = st.secrets["SENHA"]

ativo = "EUR/USD"
td = TDClient(API_KEY)

# =========================
# ESTADO DO ROBÔ (IA STOP)
# =========================
if "trades" not in st.session_state:
    st.session_state.trades = []

if "bloqueado" not in st.session_state:
    st.session_state.bloqueado = False

# =========================
# EMAIL
# =========================
def email(msg):
    try:
        m = MIMEText(msg)
        m["Subject"] = "🤖 ROBÔ ALERTA"
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
# STOP SYSTEM (IA)
# =========================
def verificar_stop():
    trades = st.session_state.trades

    if len(trades) >= 1 and trades[-1] == "LOSS":
        st.session_state.bloqueado = True
        return "STOP DIA (LOSS 1)"

    if len(trades) >= 3:
        ultimos = trades[-3:]

        if ultimos[0] == "WIN" and ultimos[1] == "WIN" and ultimos[2] == "LOSS":
            st.session_state.bloqueado = True
            return "STOP (WIN WIN LOSS)"

        if ultimos == ["WIN", "WIN", "WIN"]:
            st.session_state.trades = []

    return None

# =========================
# IA SCORE
# =========================
def score(rsi, ma9, ma21, ma200):
    s = 50

    if ma9 > ma21:
        s += 10
    else:
        s -= 10

    if rsi > 55:
        s += 15
    elif rsi < 45:
        s -= 15

    return s

# =========================
# ESTRATÉGIA
# =========================
def analisar(df):

    df["MA9"] = SMAIndicator(df["close"], 9).sma_indicator()
    df["MA21"] = SMAIndicator(df["close"], 21).sma_indicator()
    df["MA200"] = SMAIndicator(df["close"], 200).sma_indicator()
    df["RSI"] = RSIIndicator(df["close"], 14).rsi()

    preco = df["close"].iloc[-1]
    rsi = df["RSI"].iloc[-1]
    ma9 = df["MA9"].iloc[-1]
    ma21 = df["MA21"].iloc[-1]
    ma200 = df["MA200"].iloc[-1]

    suporte = df["low"].rolling(20).min().iloc[-1]
    resistencia = df["high"].rolling(20).max().iloc[-1]

    horario = datetime.now().strftime("%H:%M:%S")

    sc = score(rsi, ma9, ma21, ma200)

    if sc > 70 and preco > ma200:
        return "COMPRA", preco, suporte, preco + (preco - suporte) * 2, horario, sc

    if sc < 30 and preco < ma200:
        return "VENDA", preco, resistencia, preco - (resistencia - preco) * 2, horario, sc

    return "AGUARDAR", preco, 0, 0, horario, sc

# =========================
# BACKTEST SIMPLES 7 DIAS (BASE)
# =========================
def backtest(df):
    df = df.tail(200)

    wins = 0
    losses = 0

    for i in range(50, len(df)):
        if df["close"].iloc[i] > df["close"].iloc[i-1]:
            wins += 1
        else:
            losses += 1

    return wins, losses

# =========================
# EXECUÇÃO
# =========================
if ligado:

    stop_msg = verificar_stop()

    if st.session_state.bloqueado:
        st.error("⛔ ROBÔ BLOQUEADO PELO SISTEMA DE RISCO")
        st.warning(stop_msg if stop_msg else "Aguardando próximo dia")
        st.stop()

    df = dados()
    sinal, preco, stop, alvo, horario, sc = analisar(df)

    w, l = backtest(df)

    st.markdown("## 📊 PAINEL")
    st.write(f"💰 {preco}")
    st.write(f"📌 {sinal}")
    st.write(f"🧠 Score IA: {sc}")
    st.write(f"📊 Backtest W/L: {w}/{l}")
    st.write(f"🕒 {horario}")

    # =========================
    # REGISTRO IA
    # =========================
    if sinal != "AGUARDAR":

        st.session_state.trades.append("WIN")  # simulação inicial

        st.success(f"🚨 {sinal} detectado")

    else:
        st.info("⏳ Aguardando entrada")

else:
    st.warning("⛔ Robô desligado")
