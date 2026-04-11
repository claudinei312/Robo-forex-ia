import streamlit as st
import pandas as pd
from twelvedata import TDClient
from ta.trend import SMAIndicator
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Robô Forex IA", layout="centered")

st.title("🤖 Robô Forex IA")

ligado = st.toggle("🔌 Ligar Robô", value=True)

ativos = ["EUR/USD", "GBP/USD", "NASDAQ"]
ativo = st.selectbox("📊 Ativo", ativos)

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

if "bias" not in st.session_state:
    st.session_state.bias = 1.0

# =========================
# EMAIL
# =========================
def enviar_email(msg):
    try:
        m = MIMEText(msg)
        m["Subject"] = "🤖 Robô Forex IA"
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
# MERCADO + CRONÔMETRO
# =========================
def mercado_fechado():
    return datetime.now().weekday() >= 5

def tempo_abertura():
    agora = datetime.now()
    dias = (7 - agora.weekday()) % 7
    if dias == 0:
        dias = 1
    return timedelta(days=dias)

# =========================
# DADOS
# =========================
def pegar_dados():
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
# NOTÍCIAS
# =========================
def noticias():
    return {
        "EUR/USD": "EUR reage a dados econômicos da zona do euro",
        "GBP/USD": "GBP instável com volatilidade política",
        "NASDAQ": "Tecnologia sensível a juros nos EUA"
    }.get(ativo, "Sem notícias relevantes no momento")

# =========================
# IA
# =========================
def analisar(df):

    df["MA9"] = SMAIndicator(df["close"], 9).sma_indicator()
    df["MA21"] = SMAIndicator(df["close"], 21).sma_indicator()
    df["RSI"] = RSIIndicator(df["close"], 14).rsi()
    df["ATR"] = AverageTrueRange(df["high"], df["low"], df["close"], 14).average_true_range()

    preco = df["close"].iloc[-1]

    score = 50
    diag = []

    if df["MA9"].iloc[-1] > df["MA21"].iloc[-1]:
        score += 20
        diag.append("📈 Tendência de alta")
    else:
        score -= 20
        diag.append("📉 Tendência de baixa")

    if df["RSI"].iloc[-1] > 55:
        score += 15
        diag.append("🟢 RSI comprador")
    elif df["RSI"].iloc[-1] < 45:
        score -= 15
        diag.append("🔴 RSI vendedor")

    score *= st.session_state.bias

    return max(0, min(100, score)), preco, df["ATR"].iloc[-1], diag

# =========================
# SINAL
# =========================
def sinal(score):
    if score >= 72:
        return "COMPRA"
    elif score <= 28:
        return "VENDA"
    return "AGUARDAR"

# =========================
# BACKTEST
# =========================
def backtest(preco):

    pos = st.session_state.posicao
    if not pos:
        return

    tipo = pos["tipo"]
    tp = pos["tp"]
    sl = pos["sl"]

    result = None

    if tipo == "COMPRA":
        if preco >= tp:
            result = "WIN"
        elif preco <= sl:
            result = "LOSS"

    elif tipo == "VENDA":
        if preco <= tp:
            result = "WIN"
        elif preco >= sl:
            result = "LOSS"

    if result:
        st.session_state.trades.append(result)
        st.session_state.posicao = None

        if result == "LOSS":
            st.session_state.bias *= 0.97
        else:
            st.session_state.bias *= 1.01

        st.session_state.bias = max(0.7, min(1.3, st.session_state.bias))

# =========================
# STATS
# =========================
def stats():
    wins = st.session_state.trades.count("WIN")
    losses = st.session_state.trades.count("LOSS")
    total = wins + losses
    winrate = (wins / total * 100) if total > 0 else 50
    return winrate, wins, losses

# =========================
# RUN
# =========================
if ligado:

    df = pegar_dados()
    score, preco, atr, diag = analisar(df)
    sig = sinal(score)

    backtest(preco)

    winrate, wins, losses = stats()

    # =========================
    # ENTRADA
    # =========================
    if sig != "AGUARDAR" and st.session_state.posicao is None:

        sl = preco - atr if sig == "COMPRA" else preco + atr
        tp = preco + (atr * 2) if sig == "COMPRA" else preco - (atr * 2)

        st.session_state.posicao = {
            "tipo": sig,
            "entrada": preco,
            "tp": tp,
            "sl": sl,
            "diagnostico": diag
        }

        enviar_email(f"{sig} {ativo} {preco}")

    # =========================
    # PAINEL
    # =========================
    st.write(f"📊 Ativo: {ativo}")
    st.write(f"💰 Preço: {preco}")
    st.write(f"🧠 Score: {round(score,2)}")
    st.write(f"📈 Winrate: {round(winrate,2)}%")
    st.write(f"🏆 Wins: {wins} | ❌ Losses: {losses}")
    st.write(f"🧠 IA Bias: {round(st.session_state.bias,2)}")

    # =========================
    # NOTÍCIAS (FIXO NO PAINEL)
    # =========================
    st.markdown("## 📰 Notícias do Mercado")
    st.info(noticias())

    # =========================
    # SINAL
    # =========================
    if sig == "COMPRA":
        st.success("🟢 COMPRA")
    elif sig == "VENDA":
        st.error("🔴 VENDA")
    else:
        st.warning("⏳ AGUARDAR")

    # =========================
    # DIAGNÓSTICO
    # =========================
    st.markdown("## 🧠 Diagnóstico IA")
    for d in diag:
        st.write(d)

    # =========================
    # POSIÇÃO
    # =========================
    if st.session_state.posicao:
        st.markdown("## 📌 Operação ativa")
        st.write(st.session_state.posicao)

    # =========================
    # CRONÔMETRO (SEM TRAVAR ROBÔ)
    # =========================
    if mercado_fechado():
        st.warning("⛔ Mercado fechado")
        st.write("⏳ Próxima abertura em:")
        st.write(tempo_abertura())

else:
    st.warning("Robô desligado")
