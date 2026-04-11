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

# =========================
# CONFIGURAÇÃO
# =========================
st.set_page_config(page_title="Robô Forex IA", layout="centered")

st.title("🤖 Robô Forex Inteligente")

st_autorefresh(interval=60000, key="refresh")

# =========================
# SECRETS
# =========================
API_KEY = st.secrets["API_KEY"]
EMAIL = st.secrets["EMAIL"]
SENHA = st.secrets["SENHA"]

ativo = "EUR/USD"
intervalo = "5min"

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

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL, SENHA)
        server.sendmail(EMAIL, EMAIL, m.as_string())
        server.quit()

    except Exception as e:
        print("Erro email:", e)

# =========================
# DADOS
# =========================
def pegar_dados():
    ts = td.time_series(
        symbol=ativo,
        interval=intervalo,
        outputsize=200
    ).as_pandas()

    ts = ts[::-1].reset_index(drop=True)

    for c in ["open", "high", "low", "close"]:
        ts[c] = pd.to_numeric(ts[c], errors="coerce")

    return ts.dropna()

# =========================
# FILTRO NOTÍCIAS
# =========================
def evitar_noticias():
    agora = datetime.now()
    return (agora.hour == 9 and agora.minute >= 25) or (agora.hour == 10 and agora.minute <= 5)

# =========================
# ESTRATÉGIA COMPLETA
# =========================
def analisar(data):

    data["MA9"] = SMAIndicator(data["close"], 9).sma_indicator()
    data["MA21"] = SMAIndicator(data["close"], 21).sma_indicator()
    data["MA200"] = SMAIndicator(data["close"], 200).sma_indicator()
    data["RSI"] = RSIIndicator(data["close"], 14).rsi()

    data["ATR"] = AverageTrueRange(
        data["high"], data["low"], data["close"], 14
    ).average_true_range()

    preco = data["close"].iloc[-1]
    ma9 = data["MA9"].iloc[-1]
    ma21 = data["MA21"].iloc[-1]
    ma200 = data["MA200"].iloc[-1]
    rsi = data["RSI"].iloc[-1]
    atr = data["ATR"].iloc[-1]

    suporte = data["low"].rolling(20).min().iloc[-1]
    resistencia = data["high"].rolling(20).max().iloc[-1]

    candle = data.iloc[-1]
    corpo = abs(candle["close"] - candle["open"])
    pavio_inf = candle["open"] - candle["low"]
    pavio_sup = candle["high"] - candle["open"]

    rejeicao_compra = pavio_inf > corpo * 2
    rejeicao_venda = pavio_sup > corpo * 2

    lateral = abs(ma9 - ma21) < 0.0002

    horario = datetime.now().strftime("%H:%M:%S")

    if evitar_noticias():
        return "AGUARDAR", preco, 0, 0, horario

    if atr < 0.0003 or atr > 0.003:
        return "AGUARDAR", preco, 0, 0, horario

    # COMPRA
    if (
        preco > ma200 and
        ma9 > ma21 and
        rsi > 55 and
        preco <= suporte * 1.002 and
        rejeicao_compra and
        not lateral
    ):
        stop = suporte
        alvo = preco + (preco - stop) * 2
        return "COMPRA", preco, stop, alvo, horario

    # VENDA
    if (
        preco < ma200 and
        ma9 < ma21 and
        rsi < 45 and
        preco >= resistencia * 0.998 and
        rejeicao_venda and
        not lateral
    ):
        stop = resistencia
        alvo = preco - (stop - preco) * 2
        return "VENDA", preco, stop, alvo, horario

    return "AGUARDAR", preco, 0, 0, horario

# =========================
# EXECUÇÃO
# =========================
try:

    data = pegar_dados()
    sinal, preco, stop, alvo, horario = analisar(data)

    st.success("🟢 Robô rodando")

    st.markdown("## 📊 Mercado")
    st.write(f"💰 Preço: {preco}")
    st.write(f"📌 Sinal: {sinal}")
    st.write(f"🛑 Stop: {stop}")
    st.write(f"🎯 Alvo: {alvo}")
    st.write(f"🕒 Hora: {horario}")

except Exception as e:
    st.error("❌ Erro no robô")
    st.exception(e)
