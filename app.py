import streamlit as st
import pandas as pd
from twelvedata import TDClient
from ta.trend import SMAIndicator
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange
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
def score(rsi, ma9, ma21, ma200):
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
    df["MA200"] = SMAIndicator(df["close"], 200).sma_indicator()
    df["RSI"] = RSIIndicator(df["close"], 14).rsi()

    preco = df["close"].iloc[-1]
    ma9 = df["MA9"].iloc[-1]
    ma21 = df["MA21"].iloc[-1]
    ma200 = df["MA200"].iloc[-1]
    rsi = df["RSI"].iloc[-1]

    suporte = df["low"].rolling(20).min().iloc[-1]
    resistencia = df["high"].rolling(20).max().iloc[-1]

    horario = datetime.now().strftime("%H:%M:%S")

    sc = score(rsi, ma9, ma21, ma200)

    if sc > 70 and preco > ma200:
        return "COMPRA", preco, suporte, preco + (preco - suporte) * 2, horario, sc

    if sc < 30 and preco < ma200:
        return "VENDA", preco, resistencia, preco - (resistencia - preco) * 2, horario, sc

    return "AGUARDAR", preco, 0, 0, horario, sc

# =========================
# NOTÍCIAS
# =========================
def noticias():
    try:
        url = f"https://api.twelvedata.com/news?symbol={ativo}&apikey={API_KEY}"
        r = requests.get(url).json()
        return r.get("data", [])[:5]
    except:
        return []

# =========================
# RUN
# =========================
if ligado:

    df = dados()
    sinal, preco, stop, alvo, horario, sc = analisar(df)
    news = noticias()

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
    # ALERTAS
    # =========================
    if sinal == "COMPRA":
        st.success("🟢 COMPRA DETECTADA")
        enviar_email(f"COMPRA {ativo} preço {preco} horário {horario}")

    elif sinal == "VENDA":
        st.error("🔴 VENDA DETECTADA")
        enviar_email(f"VENDA {ativo} preço {preco} horário {horario}")

    else:
        st.info("⏳ Aguardando entrada")

    # =========================
    # NOTÍCIAS
    # =========================
    st.markdown("## 📰 Notícias do Mercado")

    if news:
        for n in news:
            st.write("•", n.get("title"))
    else:
        st.write("Sem notícias no momento")

else:
    st.warning("⛔ Robô desligado")
