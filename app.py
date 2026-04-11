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
import time

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="IA Forex Pro", layout="centered")

ativo = "EUR/USD"
st.title(f"🤖 IA Forex Pro - {ativo}")

st_autorefresh(interval=60000, key="refresh")

ligado = st.toggle("🔌 Ligar Robô", value=True)

# =========================
# SECRETS (Streamlit)
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

if "score_buy" not in st.session_state:
    st.session_state.score_buy = 72

if "score_sell" not in st.session_state:
    st.session_state.score_sell = 28

if "last_opt" not in st.session_state:
    st.session_state.last_opt = time.time()

# =========================
# EMAIL
# =========================
def enviar_email(msg):
    try:
        m = MIMEText(msg)
        m["Subject"] = "🤖 IA FOREX ALERTA"
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
# MERCADO STATUS + COUNTDOWN
# =========================
def mercado_status():

    agora = datetime.utcnow()
    dia = agora.weekday()

    abertura = agora.replace(hour=22, minute=0, second=0, microsecond=0)

    # sábado fechado
    if dia == 5:
        prox = agora + timedelta(days=1)
        prox = prox.replace(hour=22, minute=0)
        return False, prox

    # domingo antes da abertura
    if dia == 6 and agora < abertura:
        return False, abertura

    return True, None


def countdown(abertura):

    if abertura is None:
        return None

    agora = datetime.utcnow()
    diff = abertura - agora

    horas = diff.seconds // 3600
    minutos = (diff.seconds % 3600) // 60

    return f"{horas}h {minutos}m"

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

    if ma9 > ma21:
        score += 20
    else:
        score -= 20

    if rsi > 55:
        score += 15
    elif rsi < 45:
        score -= 15

    if 0.0003 < atr < 0.003:
        score += 10
    else:
        score -= 10

    score *= st.session_state.model_bias
    score = max(0, min(100, score))

    horario = datetime.now().strftime("%H:%M:%S")

    return score, preco, ma9, ma21, rsi, atr, horario

# =========================
# DECISÃO
# =========================
def decidir(score):

    if score >= st.session_state.score_buy:
        return "COMPRA"

    if score <= st.session_state.score_sell:
        return "VENDA"

    return "AGUARDAR"

# =========================
# BACKTEST SIMPLES
# =========================
def backtest():

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

    if winrate < 45:
        st.session_state.model_bias *= 0.98

    elif winrate > 60:
        st.session_state.model_bias *= 1.01

    st.session_state.model_bias = max(0.8, min(1.2, st.session_state.model_bias))

# =========================
# RUN
# =========================
if ligado:

    ativo_ok, abertura = mercado_status()

    st.markdown("## 📊 Painel IA Forex")

    if not ativo_ok:

        st.error("⛔ MERCADO FECHADO")

        st.warning(f"⏳ Abre em: {countdown(abertura)}")

        df = dados()

        score, preco, ma9, ma21, rsi, atr, horario = probabilidade(df)

        st.write(f"🧠 IA standby score: {round(score,2)}")
        st.write(f"💰 Último preço: {preco}")

    else:

        df = dados()

        score, preco, ma9, ma21, rsi, atr, horario = probabilidade(df)

        sinal = decidir(score)

        winrate = backtest()

        aprender(winrate)

        st.write(f"💱 Ativo: {ativo}")
        st.write(f"💰 Preço: {preco}")
        st.write(f"🧠 Score IA: {round(score,2)}")
        st.write(f"📊 Winrate: {round(winrate,2)}%")
        st.write(f"⚙️ IA Bias: {round(st.session_state.model_bias,3)}")

        # =========================
        # SINAIS
        # =========================
        if sinal == "COMPRA":

            st.success("🟢 COMPRA DETECTADA")

            enviar_email(f"COMPRA {ativo} {preco} {horario}")

            st.session_state.trades.append("WIN")

        elif sinal == "VENDA":

            st.error("🔴 VENDA DETECTADA")

            enviar_email(f"VENDA {ativo} {preco} {horario}")

            st.session_state.trades.append("LOSS")

        else:

            st.info("⏳ SEM SINAL (sem edge de mercado)")

else:

    st.warning("Robô desligado")
