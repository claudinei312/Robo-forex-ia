import streamlit as st
import pandas as pd
from twelvedata import TDClient
from ta.trend import SMAIndicator
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Robô Forex IA", layout="centered")
st.title("🤖 Robô Forex Inteligente com IA")

st_autorefresh(interval=60000, key="refresh")

# =========================
# BOTÃO LIGAR / DESLIGAR
# =========================
ligado = st.toggle("🔌 Ligar Robô", value=True)

# =========================
# SECRETS
# =========================
API_KEY = st.secrets["API_KEY"]
td = TDClient(API_KEY)

ativo = "EUR/USD"
intervalo = "5min"

# =========================
# IA SIMPLES (MEMÓRIA)
# =========================
if "historico" not in st.session_state:
    st.session_state.historico = []

def ia_avaliar(sinal):
    """
    IA simples: ajusta confiança baseada no histórico
    """
    if len(st.session_state.historico) < 5:
        return "NORMAL"

    ultimos = st.session_state.historico[-5:]

    losses = sum(1 for x in ultimos if x["resultado"] == "LOSS")

    if losses >= 3:
        return "MERCADO DIFÍCIL"
    return "NORMAL"

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
    pavio_inf = candle["open"] - candle["low"]
    pavio_sup = candle["high"] - candle["open"]

    rejeicao_compra = pavio_inf > corpo * 2
    rejeicao_venda = pavio_sup > corpo * 2

    lateral = abs(ma9 - ma21) < 0.0002

    horario = datetime.now().strftime("%H:%M:%S")

    # filtros básicos
    if atr < 0.0003 or atr > 0.003:
        return "AGUARDAR", preco, 0, 0, horario

    # COMPRA
    if (
        preco > ma200 and ma9 > ma21 and rsi > 55 and
        preco <= suporte * 1.002 and rejeicao_compra and not lateral
    ):
        return "COMPRA", preco, suporte, preco + (preco - suporte) * 2, horario

    # VENDA
    if (
        preco < ma200 and ma9 < ma21 and rsi < 45 and
        preco >= resistencia * 0.998 and rejeicao_venda and not lateral
    ):
        return "VENDA", preco, resistencia, preco - (resistencia - preco) * 2, horario

    return "AGUARDAR", preco, 0, 0, horario

# =========================
# EXECUÇÃO
# =========================
if ligado:

    df = pegar_dados()
    sinal, preco, stop, alvo, horario = analisar(df)

    nivel_ia = ia_avaliar(sinal)

    st.markdown("## 📊 Painel do Mercado")

    st.write(f"💰 Preço: {preco}")
    st.write(f"📌 Sinal: {sinal}")
    st.write(f"🧠 IA: {nivel_ia}")
    st.write(f"🛑 Stop: {stop}")
    st.write(f"🎯 Alvo: {alvo}")
    st.write(f"🕒 Hora: {horario}")

    st.markdown("---")

    if sinal == "AGUARDAR":
        st.info("⏳ Sem entrada — aguardando próxima vela")
    elif sinal == "COMPRA":
        st.success("🟢 POSSÍVEL COMPRA NA PRÓXIMA VELA")
    elif sinal == "VENDA":
        st.error("🔴 POSSÍVEL VENDA NA PRÓXIMA VELA")

else:
    st.warning("⛔ Robô desligado")
