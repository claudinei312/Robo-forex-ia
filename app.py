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
# MEMÓRIA
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
# MERCADO FECHADO
# =========================
def mercado_status():

    agora = datetime.utcnow()
    dia = agora.weekday()

    if dia == 5 or dia == 6:

        dias = (7 - dia) % 7
        if dias == 0:
            dias = 1

        abertura = agora + timedelta(days=dias)
        abertura = abertura.replace(hour=0, minute=0, second=0, microsecond=0)

        return False, abertura

    return True, None


def countdown(abertura):
    if abertura is None:
        return None
    agora = datetime.utcnow()
    diff = abertura - agora
    return f"{diff.seconds//3600}h {(diff.seconds%3600)//60}m"

# =========================
# NOTÍCIAS
# =========================
def noticias():
    return [
        "📉 USD sob leve pressão global",
        "📊 EUR com recuperação técnica",
        "⚠️ Alta volatilidade esperada",
        "🧠 Mercado sem tendência clara"
    ]

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
def score(df):

    df["MA9"] = SMAIndicator(df["close"], 9).sma_indicator()
    df["MA21"] = SMAIndicator(df["close"], 21).sma_indicator()
    df["RSI"] = RSIIndicator(df["close"], 14).rsi()
    df["ATR"] = AverageTrueRange(df["high"], df["low"], df["close"], 14).average_true_range()

    preco = df["close"].iloc[-1]
    atr = df["ATR"].iloc[-1]

    s = 50

    if df["MA9"].iloc[-1] > df["MA21"].iloc[-1]:
        s += 20
    else:
        s -= 20

    if df["RSI"].iloc[-1] > 55:
        s += 15
    elif df["RSI"].iloc[-1] < 45:
        s -= 15

    s *= st.session_state.model_bias
    s = max(0, min(100, s))

    return s, preco, atr

# =========================
# SINAL
# =========================
def decidir(s):

    if s >= 72:
        return "COMPRA"
    if s <= 28:
        return "VENDA"
    return "AGUARDAR"

# =========================
# BACKTEST PROFISSIONAL (TP/SL ATR)
# =========================
def backtest(preco, atr):

    pos = st.session_state.posicao

    if pos is None:
        return

    tipo = pos["tipo"]
    entrada = pos["entrada"]
    sl = pos["sl"]
    tp = pos["tp"]

    resultado = None
    motivo = ""

    if tipo == "COMPRA":

        if preco >= tp:
            resultado = "WIN"
            motivo = "TP atingido"
        elif preco <= sl:
            resultado = "LOSS"
            motivo = "Stop Loss atingido"

    elif tipo == "VENDA":

        if preco <= tp:
            resultado = "WIN"
            motivo = "TP atingido"
        elif preco >= sl:
            resultado = "LOSS"
            motivo = "Stop Loss atingido"

    if resultado:

        st.session_state.trades.append(resultado)

        st.session_state.last_result = motivo

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

    ativo_ok, abertura = mercado_status()

    st.markdown("## 📊 IA Forex Pro Dashboard")

    for n in noticias():
        st.write(n)

    if not ativo_ok:
        st.error("⛔ MERCADO FECHADO")
        st.warning(f"⏳ Abre em: {countdown(abertura)}")

    df = dados()

    s, preco, atr = score(df)

    sinal = decidir(s)

    backtest(preco, atr)

    winrate, wins, losses = stats()

    # =========================
    # ENTRADA
    # =========================
    if ativo_ok and sinal != "AGUARDAR" and st.session_state.posicao is None:

        if sinal == "COMPRA":
            sl = preco - atr
            tp = preco + (atr * 2)

        else:
            sl = preco + atr
            tp = preco - (atr * 2)

        st.session_state.posicao = {
            "tipo": sinal,
            "entrada": preco,
            "sl": sl,
            "tp": tp
        }

        enviar_email(f"{sinal} {ativo} {preco}")

    # =========================
    # PAINEL
    # =========================
    st.write(f"💱 Ativo: {ativo}")
    st.write(f"💰 Preço: {preco}")
    st.write(f"🧠 Score: {round(s,2)}")

    st.write(f"📊 Winrate: {round(winrate,2)}%")
    st.write(f"📈 Wins: {wins} | ❌ Losses: {losses}")

    if st.session_state.posicao:
        st.warning(f"📌 Operação: {st.session_state.posicao}")

    if "last_result" in st.session_state:
        st.info(f"📊 Último resultado: {st.session_state.last_result}")

else:
    st.warning("Robô desligado")
