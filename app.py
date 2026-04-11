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
# UI LAYOUT PRO
# =========================
st.set_page_config(page_title="Trading IA Pro", layout="wide")

st.markdown("""
<style>
.big {font-size:28px;font-weight:bold;color:#00ffcc;}
.card {padding:15px;border-radius:10px;background:#111827;margin:5px;}
.buy {color:#00ff00;font-size:20px;font-weight:bold;}
.sell {color:#ff3b3b;font-size:20px;font-weight:bold;}
.wait {color:#ffd166;font-size:18px;}
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='big'>🤖 IA TRADING DESK PRO</div>", unsafe_allow_html=True)

# =========================
# ATIVOS
# =========================
ativos = ["EUR/USD", "GBP/USD", "NASDAQ"]
ativo = st.sidebar.selectbox("📊 Ativo", ativos)
ligado = st.sidebar.toggle("🔌 Robô", value=True)

# =========================
# API
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

if "bias" not in st.session_state:
    st.session_state.bias = 1.0

# =========================
# EMAIL
# =========================
def send_email(msg):
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
        outputsize=150
    ).as_pandas()

    df = df[::-1].reset_index(drop=True)

    for c in ["open","high","low","close"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    return df.dropna()

# =========================
# NOTÍCIAS
# =========================
def news():
    return {
        "EUR/USD": "EUR fortalecido após dados econômicos",
        "GBP/USD": "GBP volátil com incerteza política",
        "NASDAQ": "Tech reage a juros estáveis"
    }.get(ativo, "Mercado neutro")

# =========================
# IA SCORE
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

    score *= st.session_state.bias

    return max(0, min(100, score)), price, df["ATR"].iloc[-1]

# =========================
# SINAL
# =========================
def signal(score):
    if score >= 72:
        return "BUY"
    elif score <= 28:
        return "SELL"
    return "WAIT"

# =========================
# BACKTEST COMPLETO
# =========================
def backtest(price):

    pos = st.session_state.posicao

    if pos is None:
        return

    tp = pos["tp"]
    sl = pos["sl"]

    result = None

    if pos["type"] == "BUY":
        if price >= tp:
            result = "WIN"
        elif price <= sl:
            result = "LOSS"

    if pos["type"] == "SELL":
        if price <= tp:
            result = "WIN"
        elif price >= sl:
            result = "LOSS"

    if result:
        st.session_state.trades.append(result)
        st.session_state.posicao = None

# =========================
# STATS
# =========================
def stats():
    wins = st.session_state.trades.count("WIN")
    losses = st.session_state.trades.count("LOSS")
    total = wins + losses
    winrate = (wins/total*100) if total > 0 else 50
    return winrate, wins, losses

# =========================
# RUN
# =========================
if ligado:

    df = get_data()
    score, price, atr = ai(df)
    sig = signal(score)

    backtest(price)

    winrate, wins, losses = stats()

    # =========================
    # ENTRADA
    # =========================
    if sig != "WAIT" and st.session_state.posicao is None:

        if sig == "BUY":
            sl = price - atr
            tp = price + (atr * 2)
        else:
            sl = price + atr
            tp = price - (atr * 2)

        st.session_state.posicao = {
            "type": sig,
            "entry": price,
            "tp": tp,
            "sl": sl
        }

        send_email(f"{sig} {ativo} {price}")

    # =========================
    # DASHBOARD
    # =========================
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 💱 Ativo")
        st.write(ativo)
        st.write(price)

    with col2:
        st.markdown("### 🧠 IA Score")
        st.write(round(score,2))
        st.write(f"Bias: {round(st.session_state.bias,2)}")

    with col3:
        st.markdown("### 📊 Estatísticas")
        st.write(f"Winrate: {round(winrate,2)}%")
        st.write(f"W: {wins} | L: {losses}")

    st.markdown("---")

    # =========================
    # NOTÍCIAS
    # =========================
    st.markdown("## 📰 Notícias")
    st.info(news())

    # =========================
    # SINAL
    # =========================
    if sig == "BUY":
        st.markdown("<div class='buy'>🟢 COMPRA</div>", unsafe_allow_html=True)

    elif sig == "SELL":
        st.markdown("<div class='sell'>🔴 VENDA</div>", unsafe_allow_html=True)

    else:
        st.markdown("<div class='wait'>⏳ SEM ENTRADA</div>", unsafe_allow_html=True)

    # =========================
    # POSIÇÃO
    # =========================
    if st.session_state.posicao:
        st.write("📌 Operação ativa:", st.session_state.posicao)

else:
    st.warning("Robô desligado")
