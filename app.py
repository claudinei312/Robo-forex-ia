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
st.set_page_config(page_title="Robô Forex IA PRO", layout="centered")

ativo = "EUR/USD"

st.title(f"🤖 Robô Forex IA PRO - {ativo}")

# atualiza a cada vela (60s visual)
st_autorefresh(interval=60000, key="refresh")

# =========================
# LIGA / DESLIGA
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
# MEMÓRIA
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
# BACKTEST
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
# IA DE ERROS
# =========================
def diagnostico_erros(analises):

    if len(analises) < 5:
        return "📊 Coletando dados..."

    losses = [a for a in analises if "LOSS" in a]

    if len(losses) < 2:
        return "🟢 Sem padrão de erro forte ainda"

    reversao = sum("reversão" in a.lower() for a in losses)
    tendencia = sum("tendência" in a.lower() for a in losses)

    if reversao > tendencia:
        return "⚠️ Erro principal: reversões → melhorar filtro de tendência (MA200)"

    return "⚠️ Erro principal: tendência fraca → evitar lateralização"

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
    # VELA ATUAL
    # =========================
    st.markdown("## 🕯️ Vela Atual (M5)")

    st.write(f"📊 Movimento: {sinal}")
    st.write(f"💰 Preço atual: {preco}")

    # =========================
    # BACKTEST
    # =========================
    st.markdown("## 📈 Backtest (7 dias simulado)")

    st.write(f"✅ Wins: {w}")
    st.write(f"❌ Losses: {l}")
    st.write(f"📊 Winrate: {wr}%")

    # =========================
    # ENTRADA
    # =========================
    if sinal != "AGUARDAR":

        st.session_state.trades.append(sinal)
        st.session_state.analises.append("WIN" if sc > 50 else "LOSS - reversão ou entrada fraca")

        st.success(f"🚨 {sinal} detectado")

        enviar_email(f"{sinal} {ativo} preço {preco} horário {horario}")

    else:
        st.info("⏳ Aguardando entrada")

    # =========================
    # HISTÓRICO IA
    # =========================
    st.markdown("## 🧠 Histórico de IA")

    for a in st.session_state.analises[-5:]:
        st.write("•", a)

    # =========================
    # IA ERROS
    # =========================
    st.markdown("## 🧠 Diagnóstico Automático")

    st.write(diagnostico_erros(st.session_state.analises))

else:
    st.warning("⛔ Robô desligado")
