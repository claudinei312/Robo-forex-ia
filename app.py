 # =========================
# IMPORTS
# =========================
import streamlit as st
import pandas as pd
import time
from twelvedata import TDClient
from ta.trend import SMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange
from datetime import datetime

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="🤖 ROBÔ PRO", layout="centered")
st.title("🤖 ROBÔ FOREX IA PRO (M5 OTIMIZADO)")

ligado = st.toggle("🔌 Ligar Robô", value=True)

td = TDClient(st.secrets["API_KEY"])

# 🔥 GBP REMOVIDO
ativos = ["EUR/USD", "USD/JPY", "AUD/USD"]

# =========================
# CACHE API
# =========================
cache = {}

def pegar_dados(ativo):
    agora = time.time()

    if ativo in cache and agora - cache[ativo]["time"] < 120:
        return cache[ativo]["df"]

    try:
        df = td.time_series(
            symbol=ativo,
            interval="5min",
            outputsize=1500
        ).as_pandas()

        df = df[::-1].reset_index(drop=True)

        for c in ["open", "high", "low", "close"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")

        df = df.dropna()

        cache[ativo] = {"df": df, "time": agora}

        return df

    except:
        return None

# =========================
# INDICADORES
# =========================
def indicadores(df):
    df["MA9"] = SMAIndicator(df["close"], 9).sma_indicator()
    df["MA21"] = SMAIndicator(df["close"], 21).sma_indicator()
    df["RSI"] = RSIIndicator(df["close"], 14).rsi()
    df["ATR"] = AverageTrueRange(df["high"], df["low"], df["close"], 14).average_true_range()
    return df

# =========================
# FILTRO HORÁRIO
# =========================
def horario_valido(hora):
    return (8 <= hora <= 11) or (13 <= hora <= 17)

# =========================
# SCORE IA
# =========================
def score_ia(df):

    score = 0

    if df["MA9"].iloc[-1] > df["MA21"].iloc[-1]:
        score += 1
    else:
        score -= 1

    rsi = df["RSI"].iloc[-1]
    if rsi > 55:
        score += 1
    elif rsi < 45:
        score -= 1

    m = MACD(df["close"])
    if m.macd().iloc[-1] > m.macd_signal().iloc[-1]:
        score += 1
    else:
        score -= 1

    atr = df["ATR"].iloc[-1]
    if atr > df["ATR"].rolling(50).mean().iloc[-1]:
        score += 1
    else:
        score -= 1

    return score

# =========================
# ESTRATÉGIAS (INALTERADAS)
# =========================
def tendencia_forte(df):
    closes = df["close"].tail(10)
    alta = sum(closes.iloc[i] > closes.iloc[i-1] for i in range(1, len(closes)))
    baixa = 10 - alta

    if alta >= 8:
        return "UP"
    if baixa >= 8:
        return "DOWN"
    return "LATERAL"

def filtro_distancia(df):
    price = df["close"].iloc[-1]
    ma21 = df["MA21"].iloc[-1]
    atr = df["ATR"].iloc[-1]
    return abs(price - ma21) <= atr * 1.8

def entrada_extra(df):
    price = df["close"].iloc[-1]
    ma21 = df["MA21"].iloc[-1]
    atr = df["ATR"].iloc[-1]
    score = score_ia(df)
    trend = tendencia_forte(df)

    if trend == "UP" and score >= 2 and abs(price-ma21)<atr*0.9:
        return "COMPRA"

    if trend == "DOWN" and score <= -2 and abs(price-ma21)<atr*0.9:
        return "VENDA"

    return "AGUARDAR"

def sinal(df):

    # 🔥 FILTRO VOLATILIDADE
    if df["ATR"].iloc[-1] < df["ATR"].rolling(50).mean().iloc[-1]:
        return "AGUARDAR"

    score = score_ia(df)
    trend = tendencia_forte(df)

    if trend == "LATERAL" or not filtro_distancia(df):
        return "AGUARDAR"

    if trend == "UP" and score >= 3:
        return "COMPRA"

    if trend == "DOWN" and score <= -3:
        return "VENDA"

    return entrada_extra(df)

# =========================
# BACKTEST REAL
# =========================
def backtest(df):

    wins = 0
    losses = 0

    for i in range(100, len(df)-20):

        sub = df.iloc[:i]

        # 🔥 FILTRO HORÁRIO
        hora = datetime.now().hour
        if not horario_valido(hora):
            continue

        sig = sinal(sub)

        if sig == "AGUARDAR":
            continue

        entrada = sub["close"].iloc[-1]
        atr = sub["ATR"].iloc[-1]

        stop = atr
        take = atr

        resultado = None

        for j in range(i+1, i+20):

            high = df["high"].iloc[j]
            low = df["low"].iloc[j]

            if sig == "COMPRA":
                if low <= entrada - stop:
                    resultado = 0
                    break
                if high >= entrada + take:
                    resultado = 1
                    break

            if sig == "VENDA":
                if high >= entrada + stop:
                    resultado = 0
                    break
                if low <= entrada - take:
                    resultado = 1
                    break

        if resultado == 1:
            wins += 1
        elif resultado == 0:
            losses += 1

    total = wins + losses
    wr = (wins / total * 100) if total > 0 else 0

    return wins, losses, wr

# =========================
# EXECUÇÃO
# =========================
if ligado:

    st.markdown("## 📊 PAINEL")

    for ativo in ativos:

        df = pegar_dados(ativo)

        if df is None or df.empty:
            continue

        df = indicadores(df)

        sig = sinal(df)
        preco = df["close"].iloc[-1]
        hora = datetime.now().hour

        st.markdown(f"### {ativo}")
        st.write("Preço:", preco)
        st.write("Sinal:", sig)

        if horario_valido(hora):
            st.success("🟢 Operando")
        else:
            st.warning("⏳ Fora do horário")

        # 🔥 BACKTEST RODA 1 VEZ
        if f"bt_{ativo}" not in st.session_state:
            w, l, wr = backtest(df)
            st.session_state[f"bt_{ativo}"] = (w, l, wr)

        w, l, wr = st.session_state[f"bt_{ativo}"]

        st.write(f"Backtest → Wins: {w} | Losses: {l} | WR: {wr:.1f}%")

else:
    st.warning("Robô desligado")
