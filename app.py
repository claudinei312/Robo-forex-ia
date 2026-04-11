import streamlit as st
import pandas as pd
from twelvedata import TDClient
from ta.trend import SMAIndicator
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange
from datetime import datetime, time, timedelta
import smtplib
from email.mime.text import MIMEText

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Robô Forex IA PRO v4.1", layout="centered")

st.title("🤖 Robô Forex IA PRO v4.1")

ligado = st.toggle("🔌 Ligar Robô", value=True)

ativos = ["EUR/USD", "GBP/USD"]
ativo = st.selectbox("📊 Ativo", ativos)

API_KEY = st.secrets["API_KEY"]
EMAIL = st.secrets["EMAIL"]
SENHA = st.secrets["SENHA"]

td = TDClient(API_KEY)

# =========================
# MEMÓRIA
# =========================
if "posicao" not in st.session_state:
    st.session_state.posicao = None

if "trades" not in st.session_state:
    st.session_state.trades = []

if "erros" not in st.session_state:
    st.session_state.erros = []

if "parametros" not in st.session_state:
    st.session_state.parametros = {
        "rsi_compra": 55,
        "rsi_venda": 45,
        "score_compra": 72,
        "score_venda": 28
    }

# =========================
# EMAIL
# =========================
def enviar_email(msg):
    try:
        m = MIMEText(msg)
        m["Subject"] = "🤖 Robô Forex PRO"
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
# HORÁRIO
# =========================
def mercado_aberto():
    return datetime.now().weekday() < 5

def fim_de_semana():
    return datetime.now().weekday() >= 5

def fase():
    agora = datetime.now().time()

    if time(6,30) <= agora < time(6,50):
        return "BACKTEST"
    elif time(6,50) <= agora < time(7,30):
        return "OTIMIZACAO"
    elif time(8,0) <= agora < time(18,0):
        return "OPERACAO"
    return "AGUARDAR"

# =========================
# DADOS
# =========================
def pegar_dados():
    try:
        df = td.time_series(
            symbol=ativo,
            interval="5min",
            outputsize=300
        ).as_pandas()

        df = df[::-1].reset_index(drop=True)

        for c in ["open","high","low","close"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")

        return df.dropna()
    except:
        return None

# =========================
# IA SCORE + DIAGNÓSTICO
# =========================
def calcular_score(df):

    df["MA9"] = SMAIndicator(df["close"], 9).sma_indicator()
    df["MA21"] = SMAIndicator(df["close"], 21).sma_indicator()
    df["RSI"] = RSIIndicator(df["close"], 14).rsi()
    df["ATR"] = AverageTrueRange(df["high"], df["low"], df["close"], 14).average_true_range()

    score = 50
    diag = []

    if df["MA9"].iloc[-1] > df["MA21"].iloc[-1]:
        score += 20
        tendencia = "alta"
        diag.append("📈 Tendência de alta")
    else:
        score -= 20
        tendencia = "baixa"
        diag.append("📉 Tendência de baixa")

    rsi = df["RSI"].iloc[-1]

    if rsi > st.session_state.parametros["rsi_compra"]:
        score += 15
        diag.append("🟢 RSI comprador")
    elif rsi < st.session_state.parametros["rsi_venda"]:
        score -= 15
        diag.append("🔴 RSI vendedor")
    else:
        diag.append("⚪ RSI neutro")

    atr = df["ATR"].iloc[-1]

    return score, tendencia, rsi, atr, diag

# =========================
# IA BLOQUEIO
# =========================
def bloqueio_ia(tendencia, rsi):
    erros = st.session_state.erros[-5:]

    for e in erros:
        if e["tendencia"] == tendencia and abs(e["rsi"] - rsi) < 5:
            return True
    return False

# =========================
# BACKTEST
# =========================
def rodar_backtest(df):

    wins = 0
    losses = 0

    for i in range(50, len(df)-1):

        sub = df.iloc[:i]
        score, tendencia, rsi, _, _ = calcular_score(sub)

        preco = sub["close"].iloc[-1]
        prox = df["close"].iloc[i+1]

        if score >= st.session_state.parametros["score_compra"]:
            if prox > preco:
                wins += 1
            else:
                losses += 1
                st.session_state.erros.append({"tendencia": tendencia, "rsi": rsi})

        elif score <= st.session_state.parametros["score_venda"]:
            if prox < preco:
                wins += 1
            else:
                losses += 1
                st.session_state.erros.append({"tendencia": tendencia, "rsi": rsi})

    total = wins + losses
    return (wins/total*100) if total > 0 else 0

# =========================
# IA OTIMIZAÇÃO
# =========================
def otimizar(df, ciclos=5):

    for _ in range(ciclos):

        melhor = 0
        melhor_param = st.session_state.parametros.copy()

        for rsi in range(50, 65, 2):
            for score in range(65, 80, 2):

                st.session_state.parametros["rsi_compra"] = rsi
                st.session_state.parametros["score_compra"] = score

                winrate = rodar_backtest(df)

                if winrate > melhor:
                    melhor = winrate
                    melhor_param = st.session_state.parametros.copy()

        st.session_state.parametros = melhor_param

# =========================
# EXECUÇÃO
# =========================
if ligado:

    df = pegar_dados()

    st.markdown("## 📊 Painel")

    if df is None or not mercado_aberto():

        st.write(f"Ativo: {ativo}")
        st.write("💰 Preço: aguardando mercado")
        st.write("🧠 IA treinando...")
        st.write("📢 Sinal: AGUARDAR")

        if fim_de_semana() and df is not None:
            otimizar(df, ciclos=10)
            winrate = rodar_backtest(df)
            st.write(f"📊 Treino IA → {winrate:.2f}%")

    else:

        fase_atual = fase()
        st.write(f"🧠 Fase: {fase_atual}")

        if fase_atual == "BACKTEST":
            winrate = rodar_backtest(df)
            st.write(f"📊 Backtest: {winrate:.2f}%")

        elif fase_atual == "OTIMIZACAO":
            otimizar(df, ciclos=3)
            st.success("IA ajustada")

        elif fase_atual == "OPERACAO":

            score, tendencia, rsi, atr, diag = calcular_score(df)
            preco = df["close"].iloc[-1]

            if bloqueio_ia(tendencia, rsi):
                sig = "AGUARDAR"
                st.warning("🚫 IA bloqueou entrada")
            else:
                if score >= st.session_state.parametros["score_compra"]:
                    sig = "COMPRA"
                elif score <= st.session_state.parametros["score_venda"]:
                    sig = "VENDA"
                else:
                    sig = "AGUARDAR"

            st.write(f"💰 Preço: {preco}")
            st.write(f"📊 Score: {score}")
            st.write(f"📢 Sinal: {sig}")

            st.markdown("## 🧠 Diagnóstico")
            for d in diag:
                st.write("•", d)

            if sig != "AGUARDAR" and st.session_state.posicao is None:

                sl = preco - atr if sig == "COMPRA" else preco + atr
                tp = preco + atr*2 if sig == "COMPRA" else preco - atr*2

                st.session_state.posicao = {
                    "tipo": sig,
                    "entrada": preco,
                    "tp": tp,
                    "sl": sl
                }

                enviar_email(f"{sig} {ativo} {preco}")

            if st.session_state.posicao:
                pos = st.session_state.posicao

                st.markdown("## 📌 Operação ativa")
                st.write(f"Tipo: {pos['tipo']}")
                st.write(f"Entrada: {pos['entrada']}")
                st.write(f"TP: {pos['tp']}")
                st.write(f"SL: {pos['sl']}")

else:
    st.warning("Robô desligado")
