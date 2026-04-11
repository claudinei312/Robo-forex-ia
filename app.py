import streamlit as st
import pandas as pd
from twelvedata import TDClient
from ta.trend import SMAIndicator
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import matplotlib.pyplot as plt
import smtplib
from email.mime.text import MIMEText
import requests

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Robô IA PRO", layout="centered")

ativo = "EUR/USD"
st.title(f"🤖 Robô Forex IA PRO - {ativo}")

st_autorefresh(interval=60000, key="refresh")

# =========================
# SECRETS
# =========================
API_KEY = st.secrets["API_KEY"]
EMAIL = st.secrets["EMAIL"]
SENHA = st.secrets["SENHA"]

td = TDClient(API_KEY)

# =========================
# ESTADO
# =========================
if "entrada_hora" not in st.session_state:
    st.session_state.entrada_hora = None

# =========================
# EMAIL
# =========================
def enviar_email(msg):
    try:
        m = MIMEText(msg)
        m["Subject"] = "🤖 ROBÔ FOREX"
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
        outputsize=100
    ).as_pandas()

    df = df[::-1].reset_index(drop=True)

    for c in ["open", "high", "low", "close"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    return df.dropna()

# =========================
# ESTRATÉGIA
# =========================
def analisar(df):

    df["MA9"] = SMAIndicator(df["close"], 9).sma_indicator()
    df["MA21"] = SMAIndicator(df["close"], 21).sma_indicator()
    df["MA200"] = SMAIndicator(df["close"], 200).sma_indicator()
    df["RSI"] = RSIIndicator(df["close"], 14).rsi()
    df["ATR"] = AverageTrueRange(df["high"], df["low"], df["close"], 14).average_true_range()

    preco = df["close"].iloc[-1]
    ma9 = df["MA9"].iloc[-1]
    ma21 = df["MA21"].iloc[-1]
    ma200 = df["MA200"].iloc[-1]
    rsi = df["RSI"].iloc[-1]

    suporte = df["low"].rolling(20).min().iloc[-1]
    resistencia = df["high"].rolling(20).max().iloc[-1]

    horario = datetime.now().strftime("%H:%M:%S")

    if rsi > 55 and ma9 > ma21 and preco > ma200:
        return "COMPRA", preco, suporte, horario

    if rsi < 45 and ma9 < ma21 and preco < ma200:
        return "VENDA", preco, resistencia, horario

    return "AGUARDAR", preco, 0, horario

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
# GRÁFICO M5
# =========================
def grafico(df):
    df = df.tail(30)

    cores = ["green" if c >= o else "red" for c, o in zip(df["close"], df["open"])]

    fig, ax = plt.subplots()

    ax.plot(df["close"].values, color="blue")

    ax.set_title("📈 Movimento M5 (últimas velas)")
    st.pyplot(fig)

# =========================
# RUN
# =========================
df = dados()
sinal, preco, nivel, horario = analisar(df)
news = noticias()

# =========================
# PAINEL
# =========================
st.markdown("## 📊 PAINEL DO MERCADO")

st.write(f"💰 Preço atual: {preco}")
st.write(f"📌 Sinal: {sinal}")
st.write(f"🕒 Horário do sinal: {horario}")
st.write(f"🧠 Ativo: {ativo}")

# entrada
if sinal != "AGUARDAR" and st.session_state.entrada_hora is None:
    st.session_state.entrada_hora = horario
    enviar_email(f"{sinal} detectado em {ativo} preço {preco}")

st.write(f"⏱ Última entrada: {st.session_state.entrada_hora}")

# =========================
# GRÁFICO
# =========================
st.markdown("## 📈 Gráfico M5")
grafico(df)

# =========================
# NOTÍCIAS
# =========================
st.markdown("## 📰 Notícias do Ativo")

if news:
    for n in news:
        st.write("•", n.get("title"))
else:
    st.write("Sem notícias no momento")

# alerta forte
st.warning("⚠️ Monitorando impacto de notícias em tempo real")
