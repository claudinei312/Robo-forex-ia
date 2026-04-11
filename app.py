import streamlit as st
import pandas as pd
from twelvedata import TDClient
from ta.trend import SMAIndicator
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange
import smtplib
from email.mime.text import MIMEText

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="IA Forex Pro", layout="centered")

st.title("🤖 Robô Forex IA Pro")

# =========================
# BOTÃO LIGA/DESLIGA
# =========================
ligado = st.toggle("🔌 Ligar Robô", value=True)

# =========================
# ATIVOS
# =========================
ativos = ["EUR/USD", "GBP/USD", "NASDAQ"]
ativo = st.selectbox("📊 Ativo", ativos)

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

if "bias" not in st.session_state:
    st.session_state.bias = 1.0

if "diagnostico" not in st.session_state:
    st.session_state.diagnostico = ""

# =========================
# EMAIL
# =========================
def enviar_email(msg):
    try:
        m = MIMEText(msg)
        m["Subject"] = "🤖 IA ALERTA"
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
def pegar_dados():

    df = td.time_series(
        symbol=ativo,
        interval="5min",
        outputsize=120
    ).as_pandas()

    df = df[::-1].reset_index(drop=True)

    for c in ["open","high","low","close"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    return df.dropna()

# =========================
# NOTÍCIAS
# =========================
def noticias():
    return {
        "EUR/USD": "EUR reage a dados econômicos positivos",
        "GBP/USD": "GBP instável com volatilidade política",
        "NASDAQ": "Tech segue sensível a juros"
    }.get(ativo, "Mercado neutro")

# =========================
# IA + SCORE + DIAGNÓSTICO
# =========================
def analisar(df):

    df["MA9"] = SMAIndicator(df["close"], 9).sma_indicator()
    df["MA21"] = SMAIndicator(df["close"], 21).sma_indicator()
    df["RSI"] = RSIIndicator(df["close"], 14).rsi()
    df["ATR"] = AverageTrueRange(df["high"], df["low"], df["close"], 14).average_true_range()

    price = df["close"].iloc[-1]

    score = 50
    diag = []

    # tendência
    if df["MA9"].iloc[-1] > df["MA21"].iloc[-1]:
        score += 20
        diag.append("📈 Tendência de alta (MA9 > MA21)")
    else:
        score -= 20
        diag.append("📉 Tendência de baixa (MA9 < MA21)")

    # RSI
    if df["RSI"].iloc[-1] > 55:
        score += 15
        diag.append("🟢 RSI forte comprador")
    elif df["RSI"].iloc[-1] < 45:
        score -= 15
        diag.append("🔴 RSI forte vendedor")
    else:
        diag.append("⚪ RSI neutro")

    return max(0, min(100, score)), price, df["ATR"].iloc[-1], diag

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
# BACKTEST + IA APRENDIZADO
# =========================
def backtest(preco):

    pos = st.session_state.posicao

    if not pos:
        return

    tipo = pos["tipo"]
    tp = pos["tp"]
    sl = pos["sl"]

    result = None
    motivo = ""

    if tipo == "COMPRA":
        if preco >= tp:
            result = "WIN"
            motivo = "TP atingido"
        elif preco <= sl:
            result = "LOSS"
            motivo = "Stop atingido"

    if tipo == "VENDA":
        if preco <= tp:
            result = "WIN"
            motivo = "TP atingido"
        elif preco >= sl:
            result = "LOSS"
            motivo = "Stop atingido"

    if result:

        st.session_state.trades.append(result)

        # 🧠 IA aprende
        if result == "LOSS":
            st.session_state.bias *= 0.97
            st.session_state.diagnostico = "⚠️ IA reduziu agressividade após LOSS"
        else:
            st.session_state.bias *= 1.01
            st.session_state.diagnostico = "✅ IA reforçou padrão vencedor"

        st.session_state.bias = max(0.7, min(1.3, st.session_state.bias))

        st.session_state.posicao = None

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
    st.write(f"💱 Ativo: {ativo}")
    st.write(f"💰 Preço: {preco}")
    st.write(f"🧠 Score: {round(score,2)}")
    st.write(f"📊 Winrate: {round(winrate,2)}%")
    st.write(f"📈 Wins: {wins} | ❌ Losses: {losses}")
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
    # DIAGNÓSTICO IA
    # =========================
    st.markdown("## 🧠 Diagnóstico da IA")
    for d in diag:
        st.write(d)

    if st.session_state.diagnostico:
        st.info(st.session_state.diagnostico)

    # =========================
    # POSIÇÃO
    # =========================
    if st.session_state.posicao:
        st.write("📌 Operação ativa:", st.session_state.posicao)

else:
    st.warning("Robô desligado")
