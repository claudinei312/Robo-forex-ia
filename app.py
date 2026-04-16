# =========================
# IMPORTS
# =========================
import streamlit as st
import pandas as pd
from twelvedata import TDClient
from ta.trend import SMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
import requests
import time

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="🤖 ROBÔ PRO FINAL", layout="centered")
st.title("🤖 ROBÔ FOREX IA PRO FINAL")

ligado = st.toggle("🔌 Ligar Robô", value=True)

td = TDClient(st.secrets["API_KEY"])

ativos = ["EUR/USD", "USD/JPY", "AUD/USD"]

# =========================
# EMAIL
# =========================
def enviar_email(assunto, mensagem):
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login("SEU_EMAIL", "SUA_SENHA")
        server.sendmail("SEU_EMAIL", "SEU_EMAIL", mensagem)
        server.quit()
    except:
        pass

# =========================
# CACHE
# =========================
cache = {}

def pegar_dados(ativo):
    agora = datetime.now()

    if ativo in cache:
        if (agora - cache[ativo]["time"]).seconds < 240:
            return cache[ativo]["df"]

    try:
        df = td.time_series(
            symbol=ativo,
            interval="5min",
            outputsize=1000
        ).as_pandas()

        df = df[::-1].reset_index(drop=True)

        for c in ["open","high","low","close"]:
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
    df["MA9"] = SMAIndicator(df["close"],9).sma_indicator()
    df["MA21"] = SMAIndicator(df["close"],21).sma_indicator()
    df["RSI"] = RSIIndicator(df["close"],14).rsi()
    df["ATR"] = AverageTrueRange(df["high"],df["low"],df["close"],14).average_true_range()
    return df

# =========================
# ESTRATÉGIAS ORIGINAIS
# =========================
def estrategia_eur(df):
    score = 0

    score += 1 if df["MA9"].iloc[-1] > df["MA21"].iloc[-1] else -1

    rsi = df["RSI"].iloc[-1]
    if rsi > 55: score += 1
    elif rsi < 45: score -= 1

    m = MACD(df["close"])
    score += 1 if m.macd().iloc[-1] > m.macd_signal().iloc[-1] else -1

    if score >= 3:
        return "COMPRA"
    if score <= -3:
        return "VENDA"
    return "AGUARDAR"

def estrategia_usdjpy(df):
    price = df["close"].iloc[-1]
    ma21 = df["MA21"].iloc[-1]
    rsi = df["RSI"].iloc[-1]
    atr = df["ATR"].iloc[-1]

    if price - ma21 > atr * 1.5 and rsi > 65:
        return "VENDA"
    if price - ma21 < -atr * 1.5 and rsi < 35:
        return "COMPRA"
    return "AGUARDAR"

def estrategia_audusd(df):
    ma9 = df["MA9"].iloc[-1]
    ma21 = df["MA21"].iloc[-1]
    rsi = df["RSI"].iloc[-1]

    if ma9 > ma21 and 50 < rsi < 65:
        return "COMPRA"
    if ma9 < ma21 and 35 < rsi < 50:
        return "VENDA"
    return "AGUARDAR"

# =========================
# CONTROLADOR
# =========================
def sinal(ativo, df):
    if ativo == "EUR/USD":
        return estrategia_eur(df)
    if ativo == "USD/JPY":
        return estrategia_usdjpy(df)
    if ativo == "AUD/USD":
        return estrategia_audusd(df)

# =========================
# BACKTEST (RODA 1x)
# =========================
def backtest(ativo, df):
    df = df.tail(1000)

    wins, losses = 0,0

    for i in range(50,len(df)-1):
        sub = df.iloc[:i]
        sig = sinal(ativo, sub)

        if sig == "AGUARDAR":
            continue

        price = sub["close"].iloc[-1]
        future = df["close"].iloc[i+1]

        if (sig=="COMPRA" and future>price) or (sig=="VENDA" and future<price):
            wins +=1
        else:
            losses +=1

    total = wins+losses
    wr = (wins/total*100) if total>0 else 0

    return wr

# =========================
# NOTÍCIAS
# =========================
def noticia_perigosa():
    try:
        r = requests.get("https://nfs.faireconomy.media/ff_calendar_thisweek.json")
        news = r.json()
        now = datetime.utcnow()

        for n in news:
            if n["impact"]=="High":
                t = datetime.strptime(n["date"], "%Y-%m-%d %H:%M:%S")
                minutos = (t-now).total_seconds()/60
                if 0 < minutos < 60:
                    return True
    except:
        pass

    return False

# =========================
# EXECUÇÃO
# =========================
if ligado:

    st.markdown("## 📊 INICIANDO ANÁLISE...")

    ranking = {}

    # 🔥 BACKTEST RODA UMA VEZ
    for ativo in ativos:
        df = pegar_dados(ativo)
        if df is None:
            continue

        df = indicadores(df)
        wr = backtest(ativo, df)
        ranking[ativo] = wr

    melhor = max(ranking, key=ranking.get)

    st.markdown("## 🏆 RANKING")
    st.write(ranking)
    st.success(f"Melhor ativo: {melhor}")

    # =========================
    # OPERAÇÃO
    # =========================
    df = pegar_dados(melhor)
    df = indicadores(df)

    sig = sinal(melhor, df)
    preco = df["close"].iloc[-1]

    st.markdown(f"## 🎯 {melhor}")
    st.write("Sinal:", sig)
    st.write("Preço:", preco)

    if noticia_perigosa():
        st.error("🚨 NOTÍCIA FORTE - BLOQUEADO")
    else:
        if sig in ["COMPRA","VENDA"]:
            st.success("🔥 ENTRADA DETECTADA")
        else:
            st.warning("⏳ AGUARDANDO")

else:
    st.warning("Robô desligado")
