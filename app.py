import streamlit as st
import pandas as pd
from twelvedata import TDClient
from ta.trend import SMAIndicator
from ta.momentum import RSIIndicator
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import smtplib
from email.mime.text import MIMEText
import requests
import time

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Robô IA Evolutivo", layout="centered")

ativo = "EUR/USD"
st.title(f"🤖 Robô IA Evolutivo - {ativo}")

st_autorefresh(interval=60000, key="refresh")

# =========================
# LIGA / DESLIGA
# =========================
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

if "score_buy" not in st.session_state:
    st.session_state.score_buy = 70

if "score_sell" not in st.session_state:
    st.session_state.score_sell = 30

if "last_opt" not in st.session_state:
    st.session_state.last_opt = time.time()

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
# IA SCORE BASE
# =========================
def score(rsi, ma9, ma21):

    s = 50

    if ma9 > ma21:
        s += 15
    else:
        s -= 15

    if rsi > 55:
        s += 15
    elif rsi < 45:
        s -= 15

    return max(0, min(100, s))

# =========================
# ESTRATÉGIA DINÂMICA
# =========================
def analisar(df):

    df["MA9"] = SMAIndicator(df["close"], 9).sma_indicator()
    df["MA21"] = SMAIndicator(df["close"], 21).sma_indicator()
    df["RSI"] = RSIIndicator(df["close"], 14).rsi()

    preco = df["close"].iloc[-1]
    ma9 = df["MA9"].iloc[-1]
    ma21 = df["MA21"].iloc[-1]
    rsi = df["RSI"].iloc[-1]

    sc = score(rsi, ma9, ma21)

    horario = datetime.now().strftime("%H:%M:%S")

    if sc >= st.session_state.score_buy:
        return "COMPRA", preco, sc, horario

    if sc <= st.session_state.score_sell:
        return "VENDA", preco, sc, horario

    return "AGUARDAR", preco, sc, horario

# =========================
# BACKTEST BASE
# =========================
def backtest(df):

    df = df.tail(150)

    wins = 0
    losses = 0

    for i in range(20, len(df)):
        if df["close"].iloc[i] > df["close"].iloc[i-1]:
            wins += 1
        else:
            losses += 1

    total = wins + losses
    winrate = (wins / total) * 100 if total > 0 else 0

    return wins, losses, round(winrate, 2)

# =========================
# IA AUTO-OTIMIZAÇÃO (CADA 1H)
# =========================
def auto_otimizar(winrate):

    agora = time.time()

    if agora - st.session_state.last_opt < 3600:
        return

    # lógica simples de adaptação
    if winrate < 45:
        st.session_state.score_buy += 2
        st.session_state.score_sell -= 2

    elif winrate > 60:
        st.session_state.score_buy -= 1
        st.session_state.score_sell += 1

    st.session_state.last_opt = agora

# =========================
# RUN
# =========================
if ligado:

    df = dados()

    sinal, preco, sc, horario = analisar(df)

    w, l, wr = backtest(df)

    auto_otimizar(wr)

    # =========================
    # PAINEL
    # =========================
    st.markdown("## 📊 Painel do Robô")

    st.write(f"💱 Ativo: {ativo}")
    st.write(f"💰 Preço: {preco}")
    st.write(f"📌 Sinal: {sinal}")
    st.write(f"🧠 Score: {sc}")
    st.write(f"📊 Winrate: {wr}%")

    st.write(f"🎯 BUY LEVEL: {st.session_state.score_buy}")
    st.write(f"🎯 SELL LEVEL: {st.session_state.score_sell}")

    # =========================
    # ALERTA
    # =========================
    if sinal != "AGUARDAR":

        st.success(f"🚨 {sinal} detectado")

        enviar_email(f"{sinal} {ativo} preço {preco} horário {horario}")

        st.session_state.trades.append(sinal)

    else:
        st.info("⏳ Aguardando entrada")

    # =========================
    # IA STATUS
    # =========================
    st.markdown("## 🧠 IA Evolutiva")

    st.write("📈 Ajusta estratégia automaticamente com base no desempenho")
    st.write(f"🧠 Última otimização: {datetime.fromtimestamp(st.session_state.last_opt)}")

else:
    st.warning("⛔ Robô desligado")
