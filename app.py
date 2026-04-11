import streamlit as st
import pandas as pd
from twelvedata import TDClient
from ta.trend import SMAIndicator
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange
from datetime import datetime
import smtplib
from email.mime.text import MIMEText

# =========================
# CONFIG UI (CAMADA 2)
# =========================
st.set_page_config(page_title="Trading Desk IA", layout="wide")

st.markdown("""
    <style>
    .big-title {font-size:30px; font-weight:bold; color:#00ffcc;}
    .card {padding:15px; border-radius:10px; background:#111827; margin-bottom:10px;}
    .signal-buy {color:#00ff00; font-size:22px; font-weight:bold;}
    .signal-sell {color:#ff3b3b; font-size:22px; font-weight:bold;}
    .signal-wait {color:#ffd166; font-size:18px;}
    </style>
""", unsafe_allow_html=True)

st.markdown("<div class='big-title'>🤖 IA TRADING DESK PRO</div>", unsafe_allow_html=True)

# =========================
# ATIVOS (MULTI-ATIVO)
# =========================
ativos = ["EUR/USD", "GBP/USD", "NASDAQ"]
ativo = st.sidebar.selectbox("📊 Ativo", ativos)

ligado = st.sidebar.toggle("🔌 Ligar IA", value=True)

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

if "bias" not in st.session_state:
    st.session_state.bias = 1.0

if "streak" not in st.session_state:
    st.session_state.streak = 0

# =========================
# EMAIL
# =========================
def enviar_email(msg):
    try:
        m = MIMEText(msg)
        m["Subject"] = "IA TRADE ALERT"
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
def get_data():

    df = td.time_series(
        symbol=ativo,
        interval="5min",
        outputsize=120
    ).as_pandas()

    df = df[::-1].reset_index(drop=True)

    for c in ["open", "high", "low", "close"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    return df.dropna()

# =========================
# NOTÍCIAS (FILTRO POR ATIVO)
# =========================
def noticias():

    base = {
        "EUR/USD": "EUR forte após dados econômicos da zona euro",
        "GBP/USD": "GBP volátil com incertezas políticas",
        "NASDAQ": "Tech sobe com expectativa de juros estáveis"
    }

    return base.get(ativo, "Mercado neutro")

# =========================
# IA SCORE EVOLUTIVA
# =========================
def ai(df):

    df["MA9"] = SMAIndicator(df["close"], 9).sma_indicator()
    df["MA21"] = SMAIndicator(df["close"], 21).sma_indicator()
    df["RSI"] = RSIIndicator(df["close"], 14).rsi()
    df["ATR"] = AverageTrueRange(df["high"], df["low"], df["close"], 14).average_true_range()

    price = df["close"].iloc[-1]

    score = 50

    if df["MA9"].iloc[-1] > df["MA21"].iloc[-1]:
        score += 20
    else:
        score -= 20

    if df["RSI"].iloc[-1] > 55:
        score += 15
    elif df["RSI"].iloc[-1] < 45:
        score -= 15

    # IA EVOLUTIVA (sequência de erro)
    score *= st.session_state.bias

    return max(0, min(100, score)), price, df["ATR"].iloc[-1]

# =========================
# DECISÃO
# =========================
def signal(score):

    if score >= 72:
        return "BUY"
    elif score <= 28:
        return "SELL"
    return "WAIT"

# =========================
# IA EVOLUÇÃO (APRENDIZADO REAL)
# =========================
def learn(result):

    if result == "LOSS":
        st.session_state.streak -= 1
        st.session_state.bias *= 0.97

    elif result == "WIN":
        st.session_state.streak += 1
        st.session_state.bias *= 1.01

    st.session_state.bias = max(0.7, min(1.3, st.session_state.bias))

# =========================
# PREVISÃO VELA
# =========================
def prediction(score):

    if score > 60:
        return "📈 Probabilidade de ALTA"
    elif score < 40:
        return "📉 Probabilidade de BAIXA"
    return "⚖️ Mercado indefinido"

# =========================
# RUN
# =========================
if ligado:

    df = get_data()

    score, price, atr = ai(df)

    sig = signal(score)

    # =========================
    # IA EVOLUTIVA SIMPLES
    # =========================
    if len(st.session_state.trades) > 0:
        learn(st.session_state.trades[-1])

    # =========================
    # PAINEL (DESK PROFISSIONAL)
    # =========================
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 💱 Ativo")
        st.write(ativo)
        st.write(f"Preço: {price}")

    with col2:
        st.markdown("### 🧠 IA Score")
        st.write(round(score, 2))
        st.write(f"Bias: {round(st.session_state.bias,2)}")

    with col3:
        st.markdown("### 📊 Mercado")
        st.write(prediction(score))

    st.markdown("---")

    # =========================
    # NOTÍCIA
    # =========================
    st.markdown("## 📰 Notícia do Ativo")
    st.info(noticias())

    # =========================
    # SINAL
    # =========================
    if sig == "BUY":
        st.markdown("<div class='signal-buy'>🟢 COMPRA</div>", unsafe_allow_html=True)
        enviar_email(f"BUY {ativo} {price}")

    elif sig == "SELL":
        st.markdown("<div class='signal-sell'>🔴 VENDA</div>", unsafe_allow_html=True)
        enviar_email(f"SELL {ativo} {price}")

    else:
        st.markdown("<div class='signal-wait'>⏳ SEM ENTRADA SEGURA</div>", unsafe_allow_html=True)

    # =========================
    # STATUS IA
    # =========================
    st.markdown("---")
    st.write(f"📊 Sequência (streak): {st.session_state.streak}")

else:
    st.warning("Robô desligado")
