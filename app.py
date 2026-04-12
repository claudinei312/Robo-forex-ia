import streamlit as st
import pandas as pd
from twelvedata import TDClient
from ta.trend import SMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange
from datetime import datetime
import random

# 📊 gráfico
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# =========================
# 📩 EMAIL
# =========================
import smtplib
from email.mime.text import MIMEText

def enviar_email(assunto, mensagem):
    email = st.secrets["EMAIL"]
    senha = st.secrets["SENHA"]

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
st.set_page_config(page_title="🤖 Robô IA v9 FULL", layout="centered")
st.title("🤖 ROBÔ FOREX IA v9 - COMPLETO")

ligado = st.toggle("🔌 Ligar Robô", value=True)
ativo = st.selectbox("📊 Ativo", ["EUR/USD", "GBP/USD"])

td = TDClient(st.secrets["API_KEY"])
ativos = ["EUR/USD", "GBP/USD"]

# =========================
# NOTÍCIAS
# =========================
def noticias():
    return random.choice([
        "BAIXO IMPACTO",
        "MÉDIO IMPACTO",
        "ALTO IMPACTO ⚠️"
    ])

# =========================
# RANKING
# =========================
def ranking_ativos():
    ranking = {}

    for a in ativos:
        try:
            df = td.time_series(symbol=a, interval="15min", outputsize=200).as_pandas()
            df = df[::-1].reset_index(drop=True)

            for c in ["open","high","low","close"]:
                df[c] = pd.to_numeric(df[c], errors="coerce")

            df = df.dropna()
            df = indicadores(df)

            ranking[a] = score_ia(df)
        except:
            ranking[a] = 0

    melhor = max(ranking, key=ranking.get)
    return ranking, melhor

# =========================
# DADOS
# =========================
def pegar_dados():
    try:
        df = td.time_series(symbol=ativo, interval="15min", outputsize=5000).as_pandas()
        df = df[::-1].reset_index(drop=True)

        for c in ["open","high","low","close"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")

        return df.dropna()
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
# GRÁFICO
# =========================
def grafico(df):

    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close']
    ))

    fig.add_trace(go.Scatter(x=df.index, y=df["MA9"], name="MA9"))
    fig.add_trace(go.Scatter(x=df.index, y=df["MA21"], name="MA21"))

    sig = sinal(df)

    if sig != "AGUARDAR":
        fig.add_trace(go.Scatter(
            x=[df.index[-1]],
            y=[df["close"].iloc[-1]],
            mode="markers+text",
            text=[sig],
            textposition="top center"
        ))

    fig.update_layout(height=500, xaxis_rangeslider_visible=False)

    return fig

# =========================
# IA
# =========================
def score_ia(df):
    score = 0

    score += 1 if df["MA9"].iloc[-1] > df["MA21"].iloc[-1] else -1

    rsi = df["RSI"].iloc[-1]
    if rsi > 55: score += 1
    elif rsi < 45: score -= 1

    m = MACD(df["close"])
    score += 1 if m.macd().iloc[-1] > m.macd_signal().iloc[-1] else -1

    atr = df["ATR"].iloc[-1]
    score += 1 if atr > df["ATR"].rolling(50).mean().iloc[-1] else -1

    return score

def tendencia_forte(df):
    closes = df["close"].tail(10)
    alta = sum(closes.iloc[i] > closes.iloc[i-1] for i in range(1,len(closes)))
    baixa = sum(closes.iloc[i] < closes.iloc[i-1] for i in range(1,len(closes)))

    if alta >= 8: return "UP"
    if baixa >= 8: return "DOWN"
    return "LATERAL"

def filtro_distancia(df):
    return abs(df["close"].iloc[-1] - df["MA21"].iloc[-1]) <= df["ATR"].iloc[-1]*1.8

def entrada_extra(df):
    price = df["close"].iloc[-1]
    ma21 = df["MA21"].iloc[-1]
    atr = df["ATR"].iloc[-1]

    if tendencia_forte(df) == "UP" and score_ia(df) >= 2 and abs(price-ma21)<atr*0.9 and df["close"].iloc[-1]>df["close"].iloc[-2]:
        return "COMPRA"

    if tendencia_forte(df) == "DOWN" and score_ia(df) <= -2 and abs(price-ma21)<atr*0.9 and df["close"].iloc[-1]<df["close"].iloc[-2]:
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
# HORÁRIO
# =========================
def horario():
    now = datetime.now()
    return now.hour >= 8 and now.weekday() < 5

# =========================
# EXECUÇÃO
# =========================
if ligado:

    st_autorefresh(interval=60000)

    df = pegar_dados()

    if df is not None:

        df = indicadores(df)

        sinal_atual = sinal(df)
        preco = df["close"].iloc[-1]

        impacto = noticias()
        ranking, melhor = ranking_ativos()

        if horario():
            if sinal_atual == "COMPRA":
                enviar_email("COMPRA", f"{ativo} {preco}")
            if sinal_atual == "VENDA":
                enviar_email("VENDA", f"{ativo} {preco}")
        else:
            sinal_atual = "AGUARDAR"

        st.write("Ativo:", ativo)
        st.write("Preço:", preco)
        st.write("Sinal:", sinal_atual)

        st.plotly_chart(grafico(df), use_container_width=True)

        st.write("Notícias:", impacto)
        st.write("Ranking:", ranking)
        st.write("Melhor:", melhor)
