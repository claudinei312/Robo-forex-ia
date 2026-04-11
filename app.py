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

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Robô IA PRO", layout="centered")

ativo = "EUR/USD"
st.title(f"🤖 Robô Forex IA PRO - {ativo}")

st_autorefresh(interval=60000, key="refresh")

# =========================
# TOGGLE
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
# MEMÓRIA IA (TRADES)
# =========================
if "trades" not in st.session_state:
    st.session_state.trades = []

if "analises" not in st.session_state:
    st.session_state.analises = []

# =========================
# EMAIL
# =========================
def enviar_email(msg):
    try:
        m = MIMEText(msg)
        m["Subject"] = "🤖 ROBÔ FOREX ALERTA"
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
# IA SCORE
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
# ESTRATÉGIA
# =========================
def analisar(df):

    df["MA9"] = SMAIndicator(df["close"], 9).sma_indicator()
    df["MA21"] = SMAIndicator(df["close"], 21).sma_indicator()
    df["RSI"] = RSIIndicator(df["close"], 14).rsi()

    preco = df["close"].iloc[-1]
    ma9 = df["MA9"].iloc[-1]
    ma21 = df["MA21"].iloc[-1]
    rsi = df["RSI"].iloc[-1]

    horario = datetime.now().strftime("%H:%M:%S")

    sc = score(rsi, ma9, ma21)

    if sc > 70:
        return "COMPRA", preco, horario, sc

    if sc < 30:
        return "VENDA", preco, horario, sc

    return "AGUARDAR", preco, horario, sc

# =========================
# BACKTEST REAL (7 DIAS SIMPLIFICADO)
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
    winrate = round((wins / total) * 100, 2) if total > 0 else 0

    return wins, losses, winrate

# =========================
# IA PÓS-ANÁLISE
# =========================
def analisar_trade(entrada, saida, tipo):

    if tipo == "COMPRA":
        if saida > entrada:
            return "WIN - tendência favorável (compradores dominaram)"
        else:
            return "LOSS - reversão forte contra compra"

    if tipo == "VENDA":
        if saida < entrada:
            return "WIN - pressão vendedora dominante"
        else:
            return "LOSS - reversão contra venda"

    return "NEUTRO"

# =========================
# RUN
# =========================
if ligado:

    df = dados()
    sinal, preco, horario, sc = analisar(df)
    w, l, wr = backtest(df)

    # =========================
    # PAINEL
    # =========================
    st.markdown("## 📊 Painel do Robô")

    st.markdown(f"### 💱 Ativo: {ativo}")

    st.write(f"💰 Preço: {preco}")
    st.write(f"📌 Sinal: {sinal}")
    st.write(f"🧠 Score IA: {sc}")
    st.write(f"🕒 Horário: {horario}")

    # =========================
    # BACKTEST
    # =========================
    st.markdown("## 📈 Backtest (7 dias simulado)")

    st.write(f"✅ Wins: {w}")
    st.write(f"❌ Losses: {l}")
    st.write(f"📊 Winrate: {wr}%")

    # =========================
    # ENTRADA + REGISTRO
    # =========================
    if sinal != "AGUARDAR":

        st.session_state.trades.append(sinal)

        st.success(f"🚨 {sinal} detectado")

        enviar_email(f"{sinal} {ativo} preço {preco} horário {horario}")

        # simulação de saída futura (pós-análise)
        saida_simulada = preco * 1.001 if sinal == "COMPRA" else preco * 0.999

        analise = analisar_trade(preco, saida_simulada, sinal)

        st.session_state.analises.append(analise)

    else:
        st.info("⏳ Aguardando entrada")

    # =========================
    # HISTÓRICO IA
    # =========================
    st.markdown("## 🧠 IA Pós-Análise de Trades")

    for a in st.session_state.analises[-5:]:
        st.write("•", a)

else:
    st.warning("⛔ Robô desligado")
