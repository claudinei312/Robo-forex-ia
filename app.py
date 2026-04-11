import streamlit as st
import pandas as pd
from twelvedata import TDClient
from ta.trend import SMAIndicator
from ta.momentum import RSIIndicator
from datetime import datetime, time
import smtplib
from email.mime.text import MIMEText

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Robô Forex IA PRO v3", layout="centered")

st.title("🤖 Robô Forex IA PRO v3")

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
def fase():
    agora = datetime.now().time()

    if time(6,30) <= agora < time(6,50):
        return "BACKTEST"
    elif time(6,50) <= agora < time(7,30):
        return "OTIMIZACAO"
    elif time(8,0) <= agora < time(18,0):
        return "OPERACAO"
    return "AGUARDAR"

def mercado_aberto():
    return datetime.now().weekday() < 5

# =========================
# DADOS
# =========================
def pegar_dados():
    df = td.time_series(
        symbol=ativo,
        interval="5min",
        outputsize=200
    ).as_pandas()

    df = df[::-1].reset_index(drop=True)

    for c in ["open","high","low","close"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    return df.dropna()

# =========================
# SCORE + DIAGNÓSTICO
# =========================
def calcular_score(df):

    df["MA9"] = SMAIndicator(df["close"], 9).sma_indicator()
    df["MA21"] = SMAIndicator(df["close"], 21).sma_indicator()
    df["RSI"] = RSIIndicator(df["close"], 14).rsi()

    score = 50
    diag = []

    if df["MA9"].iloc[-1] > df["MA21"].iloc[-1]:
        score += 20
        tendencia = "alta"
        diag.append("📈 Alta")
    else:
        score -= 20
        tendencia = "baixa"
        diag.append("📉 Baixa")

    rsi = df["RSI"].iloc[-1]

    if rsi > st.session_state.parametros["rsi_compra"]:
        score += 15
        diag.append("RSI compra")
    elif rsi < st.session_state.parametros["rsi_venda"]:
        score -= 15
        diag.append("RSI venda")

    return score, tendencia, rsi, diag

# =========================
# IA ANTI-ERRO
# =========================
def bloqueio_ia(tendencia, rsi):

    erros = st.session_state.erros[-5:]

    for e in erros:
        if e["tendencia"] == tendencia and abs(e["rsi"] - rsi) < 5:
            return True

    return False

# =========================
# BACKTEST + APRENDIZADO
# =========================
def rodar_backtest(df):

    wins = 0
    losses = 0

    for i in range(50, len(df)-1):

        sub = df.iloc[:i]
        score, tendencia, rsi, _ = calcular_score(sub)

        preco = sub["close"].iloc[-1]
        prox = df["close"].iloc[i+1]

        if score >= st.session_state.parametros["score_compra"]:

            if prox > preco:
                wins += 1
            else:
                losses += 1
                st.session_state.erros.append({
                    "tendencia": tendencia,
                    "rsi": rsi
                })

        elif score <= st.session_state.parametros["score_venda"]:

            if prox < preco:
                wins += 1
            else:
                losses += 1
                st.session_state.erros.append({
                    "tendencia": tendencia,
                    "rsi": rsi
                })

    total = wins + losses
    winrate = (wins/total*100) if total > 0 else 0

    return winrate, wins, losses

# =========================
# OTIMIZAÇÃO
# =========================
def otimizar(df):

    melhor = 0
    melhor_param = st.session_state.parametros.copy()

    for rsi in range(50, 65, 2):
        for score in range(65, 80, 2):

            st.session_state.parametros["rsi_compra"] = rsi
            st.session_state.parametros["score_compra"] = score

            winrate, _, _ = rodar_backtest(df)

            if winrate > melhor:
                melhor = winrate
                melhor_param = st.session_state.parametros.copy()

    st.session_state.parametros = melhor_param

# =========================
# EXECUÇÃO
# =========================
if ligado:

    df = pegar_dados()
    fase_atual = fase()

    st.write(f"🧠 Fase: {fase_atual}")

    # BACKTEST
    if fase_atual == "BACKTEST":
        winrate, wins, losses = rodar_backtest(df)
        st.write(f"Winrate: {winrate:.2f}%")

    # OTIMIZAÇÃO
    elif fase_atual == "OTIMIZACAO":
        otimizar(df)
        st.success("IA otimizou parâmetros")

    # OPERAÇÃO
    elif fase_atual == "OPERACAO":

        score, tendencia, rsi, diag = calcular_score(df)
        preco = df["close"].iloc[-1]

        if bloqueio_ia(tendencia, rsi):
            st.warning("🚫 IA bloqueou entrada (padrão ruim)")
            sig = "AGUARDAR"
        else:
            if score >= st.session_state.parametros["score_compra"]:
                sig = "COMPRA"
            elif score <= st.session_state.parametros["score_venda"]:
                sig = "VENDA"
            else:
                sig = "AGUARDAR"

        st.write(f"Sinal: {sig}")
        st.write(f"Score: {score}")

        # ENTRADA
        if sig != "AGUARDAR" and st.session_state.posicao is None:

            st.session_state.posicao = {
                "tipo": sig,
                "entrada": preco,
                "diag": diag
            }

            if mercado_aberto():
                enviar_email(f"{sig} {ativo} {preco}")

        # MONITORAMENTO
        if st.session_state.posicao:
            pos = st.session_state.posicao

            st.markdown("## 📌 Operação ativa")
            st.write(f"Tipo: {pos['tipo']}")
            st.write(f"Entrada: {pos['entrada']}")

    else:
        st.warning("⏳ Aguardando horário ideal")

else:
    st.warning("Robô desligado")
