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
        m["Subject"] = "🤖 Robô Forex"
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
def mercado_fechado():
    dia = datetime.now().weekday()
    return dia >= 5  # sábado e domingo

def tempo_abertura():
    agora = datetime.now()
    dias = (7 - agora.weekday()) % 7
    if dias == 0:
        dias = 1
    prox = agora + timedelta(days=dias)
    return prox - agora

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
        "EUR/USD": "EUR reage a dados econômicos",
        "GBP/USD": "GBP instável no mercado",
        "NASDAQ": "Tech volátil com juros"
    }.get(ativo, "Sem impacto relevante")

# =========================
# IA + DIAGNÓSTICO
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
# BACKTEST + STOP
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

    if mercado_fechado():
        st.error("⛔ Mercado FECHADO")
        st.write("⏳ Abre em:")
        st.write(tempo_abertura())
        st.stop()

    df = pegar_dados()
    score, preco, atr, diag = analisar(df)
    sig = sinal(score)

    backtest(preco)

    winrate, wins, losses = stats()

    # =========================
    # ENTRADA
    # =========================
    if sig != "AGUARDAR" and st.session_state.posicao is None:

        if sig == "COMPRA":
            sl = preco - atr
            tp = preco + (atr * 2)
        else:
            sl = preco + atr
            tp = preco - (atr * 2)

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
    # NOTÍCIAS
    # =========================
    st.markdown("## 📰 Notícias")
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
    # POSIÇÃO LIMPA
    # =========================
    if st.session_state.posicao:
        st.markdown("## 📌 Operação ativa")
        st.write(f"Tipo: {st.session_state.posicao['tipo']}")
        st.write(f"Entrada: {st.session_state.posicao['entrada']}")
        st.write(f"TP: {st.session_state.posicao['tp']}")
        st.write(f"SL: {st.session_state.posicao['sl']}")

else:
    st.warning("Robô desligado")
