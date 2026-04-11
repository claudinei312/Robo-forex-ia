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
st.set_page_config(page_title="Robô Forex IA HARD", layout="centered")

st.title("🤖 Robô Forex IA HARD LEVEL")

st_autorefresh(interval=60000, key="refresh")

# =========================
# SECRETS
# =========================
API_KEY = st.secrets["API_KEY"]
EMAIL = st.secrets["EMAIL"]
SENHA = st.secrets["SENHA"]

ativo = "EUR/USD"

td = TDClient(API_KEY)

# =========================
# EMAIL SYSTEM
# =========================
def enviar_email(msg):
    try:
        m = MIMEText(msg)
        m["Subject"] = "🤖 ALERTA ROBÔ FOREX"
        m["From"] = EMAIL
        m["To"] = EMAIL

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL, SENHA)
        server.sendmail(EMAIL, EMAIL, m.as_string())
        server.quit()
    except:
        pass

# =========================
# NOTÍCIAS (NOVO)
# =========================
def buscar_noticias():
    try:
        url = f"https://api.twelvedata.com/news?symbol={ativo}&apikey={API_KEY}"
        r = requests.get(url).json()

        if "data" in r:
            return r["data"][:3]
        return []
    except:
        return []

def impacto_noticia(noticias):
    for n in noticias:
        texto = (n.get("title", "") + n.get("description", "")).lower()

        if any(x in texto for x in ["federal", "inflation", "interest", "rate", "fed"]):
            return True, n.get("title")

    return False, None

# =========================
# DADOS
# =========================
def pegar_dados():
    ts = td.time_series(
        symbol=ativo,
        interval="5min",
        outputsize=200
    ).as_pandas()

    ts = ts[::-1].reset_index(drop=True)

    for c in ["open", "high", "low", "close"]:
        ts[c] = pd.to_numeric(ts[c], errors="coerce")

    return ts.dropna()

# =========================
# IA SCORE ENGINE
# =========================
def calcular_score(rsi, ma9, ma21, ma200, lateral):
    score = 50

    if ma9 > ma21:
        score += 10
    else:
        score -= 10

    if rsi > 55:
        score += 15
    elif rsi < 45:
        score -= 15

    if not lateral:
        score += 10
    else:
        score -= 20

    return max(0, min(100, score))

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
    atr = df["ATR"].iloc[-1]

    suporte = df["low"].rolling(20).min().iloc[-1]
    resistencia = df["high"].rolling(20).max().iloc[-1]

    candle = df.iloc[-1]
    corpo = abs(candle["close"] - candle["open"])

    lateral = abs(ma9 - ma21) < 0.0002

    horario = datetime.now().strftime("%H:%M:%S")

    score = calcular_score(rsi, ma9, ma21, ma200, lateral)

    # COMPRA
    if score > 70 and preco > ma200 and ma9 > ma21:
        return "COMPRA", preco, suporte, preco + (preco - suporte) * 2, horario, score

    # VENDA
    if score < 30 and preco < ma200 and ma9 < ma21:
        return "VENDA", preco, resistencia, preco - (resistencia - preco) * 2, horario, score

    return "AGUARDAR", preco, 0, 0, horario, score

# =========================
# START ALERT
# =========================
if "start" not in st.session_state:
    st.session_state.start = True
    enviar_email("🤖 Robô iniciado com sucesso")

# =========================
# RUN
# =========================
df = pegar_dados()
sinal, preco, stop, alvo, horario, score = analisar(df)

noticias = buscar_noticias()
alerta_noticia, titulo = impacto_noticia(noticias)

# =========================
# PAINEL
# =========================
st.markdown(f"## 📊 Ativo: {ativo}")

st.write(f"💰 Preço: {preco}")
st.write(f"📌 Sinal: {sinal}")
st.write(f"🧠 IA Score: {score}/100")
st.write(f"🕒 Hora: {horario}")

# =========================
# NOTÍCIAS
# =========================
st.markdown("## 📰 Notícias")

if alerta_noticia:
    st.error(f"⚠️ IMPACTO ALTO: {titulo}")
else:
    st.success("Nenhuma notícia crítica")

for n in noticias:
    st.write("•", n.get("title"))

# =========================
# ALERTA DE ENTRADA
# =========================
if sinal == "COMPRA":
    st.success("🟢 POSSÍVEL COMPRA")
    enviar_email(f"COMPRA detectada {ativo} preço {preco}")

elif sinal == "VENDA":
    st.error("🔴 POSSÍVEL VENDA")
    enviar_email(f"VENDA detectada {ativo} preço {preco}")

else:
    st.info("⏳ Aguardando entrada")
