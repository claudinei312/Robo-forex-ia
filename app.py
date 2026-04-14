import streamlit as st
import pandas as pd
from twelvedata import TDClient
from ta.trend import SMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange
from datetime import datetime
import random
import plotly.graph_objects as go

# =========================
# EMAIL (MANTIDO)
# =========================
import smtplib
from email.mime.text import MIMEText

def enviar_email(assunto, mensagem):
    email = "claudineialvesjunior@gmail.com"
    senha = "dvuw lmde sfse tyax"

    msg = MIMEText(mensagem)
    msg["Subject"] = assunto
    msg["From"] = email
    msg["To"] = email

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(email, senha)
        server.sendmail(email, email, msg.as_string())
        server.quit()
    except:
        pass

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="🤖 Robô IA v10 PRO", layout="centered")
st.title("🤖 ROBÔ FOREX IA - MULTI ESTRATÉGIAS")

ligado = st.toggle("🔌 Ligar Robô", value=True)

td = TDClient(st.secrets["API_KEY"])
ativos = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD"]

# =========================
# DADOS (MANTIDO)
# =========================
def pegar_dados(ativo):
    try:
        df = td.time_series(
            symbol=ativo,
            interval="15min",
            outputsize=5000
        ).as_pandas()

        df = df[::-1].reset_index(drop=True)

        for c in ["open", "high", "low", "close"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")

        return df.dropna()
    except:
        return None

# =========================
# INDICADORES (MANTIDO)
# =========================
def indicadores(df):
    df["MA9"] = SMAIndicator(df["close"], 9).sma_indicator()
    df["MA21"] = SMAIndicator(df["close"], 21).sma_indicator()
    df["RSI"] = RSIIndicator(df["close"], 14).rsi()
    df["ATR"] = AverageTrueRange(df["high"], df["low"], df["close"], 14).average_true_range()
    return df

# =========================
# IA (MANTIDO)
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
# EUR/USD ORIGINAL (INTACTO)
# =========================
def tendencia_forte(df):
    closes = df["close"].tail(10)
    alta = 0
    baixa = 0
    for i in range(1, len(closes)):
        if closes.iloc[i] > closes.iloc[i-1]:
            alta += 1
        else:
            baixa += 1
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

    if trend == "UP" and score >= 2 and abs(price-ma21)<atr*0.9 and df["close"].iloc[-1] > df["close"].iloc[-2]:
        return "COMPRA"

    if trend == "DOWN" and score <= -2 and abs(price-ma21)<atr*0.9 and df["close"].iloc[-1] < df["close"].iloc[-2]:
        return "VENDA"

    return "AGUARDAR"

def sinal(df):
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
# GBP/USD
# =========================
def estrategia_gbpusd(df):
    rsi = df["RSI"].iloc[-1]
    rsi_ant = df["RSI"].iloc[-2]
    ma21 = df["MA21"].iloc[-1]
    price = df["close"].iloc[-1]
    atr = df["ATR"].iloc[-1]

    trend = tendencia_forte(df)
    distancia = abs(price - ma21)

    if trend == "UP" and distancia > atr:
        if rsi_ant < 50 and rsi > rsi_ant:
            return "COMPRA"

    if trend == "DOWN" and distancia > atr:
        if rsi_ant > 50 and rsi < rsi_ant:
            return "VENDA"

    return "AGUARDAR"

# =========================
# USD/JPY
# =========================
def estrategia_usdjpy(df):
    price = df["close"].iloc[-1]
    ma21 = df["MA21"].iloc[-1]
    rsi = df["RSI"].iloc[-1]
    atr = df["ATR"].iloc[-1]

    high_prev = df["high"].iloc[-2]
    low_prev = df["low"].iloc[-2]

    distancia = price - ma21

    if distancia > atr * 1.5 and rsi > 65:
        nivel = high_prev - (high_prev - low_prev) * 0.5
        if price < nivel:
            return "VENDA"

    if distancia < -atr * 1.5 and rsi < 35:
        nivel = low_prev + (high_prev - low_prev) * 0.5
        if price > nivel:
            return "COMPRA"

    return "AGUARDAR"

# =========================
# AUD/USD
# =========================
def estrategia_audusd(df):
    ma9 = df["MA9"].iloc[-1]
    ma21 = df["MA21"].iloc[-1]
    rsi = df["RSI"].iloc[-1]
    atr = df["ATR"].iloc[-1]

    price = df["close"].iloc[-1]
    high_prev = df["high"].iloc[-2]
    low_prev = df["low"].iloc[-2]

    if ma9 > ma21 and 50 < rsi < 65:
        if abs(price - ma9) < atr * 0.3:
            if price > high_prev:
                return "COMPRA"

    if ma9 < ma21 and 35 < rsi < 50:
        if abs(price - ma9) < atr * 0.3:
            if price < low_prev:
                return "VENDA"

    return "AGUARDAR"

# =========================
# SELETOR (SEM QUEBRAR EURUSD)
# =========================
def sinal_por_ativo(ativo, df):

    if ativo == "EUR/USD":
        return sinal(df)  # ORIGINAL

    elif ativo == "GBP/USD":
        return estrategia_gbpusd(df)

    elif ativo == "USD/JPY":
        return estrategia_usdjpy(df)

    elif ativo == "AUD/USD":
        return estrategia_audusd(df)

    return "AGUARDAR"

# =========================
# BACKTEST
# =========================
def backtest_por_ativo(df, ativo):

    wins = 0
    losses = 0

    for i in range(60, len(df)-1):

        sub = df.iloc[:i]
        sig = sinal_por_ativo(ativo, sub)

        if sig == "AGUARDAR":
            continue

        price = sub["close"].iloc[-1]
        next_price = df["close"].iloc[i+1]

        if (sig == "COMPRA" and next_price > price) or (sig == "VENDA" and next_price < price):
            wins += 1
        else:
            losses += 1

    total = wins + losses
    winrate = (wins/total*100) if total>0 else 0

    return wins, losses, total, round(winrate,2)

# =========================
# EXECUÇÃO
# =========================
if ligado:

    for ativo in ativos:

        df = pegar_dados(ativo)
        if df is None:
            continue

        df = indicadores(df)

        sig = sinal_por_ativo(ativo, df)
        preco = df["close"].iloc[-1]

        st.markdown(f"### 📊 {ativo}")
        st.write("Preço:", preco)
        st.write("Sinal:", sig)

        w,l,t,wr = backtest_por_ativo(df, ativo)

        st.write("Wins:", w)
        st.write("Losses:", l)
        st.write("Winrate:", wr,"%")

else:
    st.warning("Robô desligado")
