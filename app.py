import streamlit as st
import pandas as pd
from twelvedata import TDClient
from ta.trend import SMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange
from datetime import datetime
import random

# 📊 GRÁFICO
import plotly.graph_objects as go

# =========================
# 📩 EMAIL
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
# 🟩 CONFIG
# =========================
st.set_page_config(page_title="🤖 Robô IA v9 FULL", layout="centered")
st.title("🤖 ROBÔ FOREX IA v9 - COMPLETO")

ligado = st.toggle("🔌 Ligar Robô", value=True)
ativo = st.selectbox("📊 Ativo", ["EUR/USD", "GBP/USD"])

td = TDClient(st.secrets["API_KEY"])

ativos = ["EUR/USD", "GBP/USD"]

# =========================
# 📰 NOTÍCIAS
# =========================
def noticias():
    return random.choice([
        "BAIXO IMPACTO",
        "MÉDIO IMPACTO",
        "ALTO IMPACTO ⚠️"
    ])

# =========================
# 🏆 RANKING
# =========================
def ranking_ativos():

    ranking = {}

    for a in ativos:
        try:
            df = td.time_series(
                symbol=a,
                interval="15min",
                outputsize=200
            ).as_pandas()

            df = df[::-1].reset_index(drop=True)

            for c in ["open", "high", "low", "close"]:
                df[c] = pd.to_numeric(df[c], errors="coerce")

            df = df.dropna()

            df = indicadores(df)

            score = score_ia(df)

            ranking[a] = score

        except:
            ranking[a] = 0

    melhor = max(ranking, key=ranking.get)

    return ranking, melhor

# =========================
# 🟦 DADOS
# =========================
def pegar_dados():
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
# 🟩 INDICADORES
# =========================
def indicadores(df):
    df["MA9"] = SMAIndicator(df["close"], 9).sma_indicator()
    df["MA21"] = SMAIndicator(df["close"], 21).sma_indicator()
    df["RSI"] = RSIIndicator(df["close"], 14).rsi()
    df["ATR"] = AverageTrueRange(df["high"], df["low"], df["close"], 14).average_true_range()
    return df

# =========================
# 📈 GRÁFICO LIMPO (AJUSTADO)
# =========================
def mostrar_grafico(df):

    df_plot = df.tail(30)

    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=df_plot.index,
        open=df_plot['open'],
        high=df_plot['high'],
        low=df_plot['low'],
        close=df_plot['close']
    ))

    fig.add_trace(go.Scatter(
        x=df_plot.index,
        y=df_plot["MA9"],
        line=dict(width=1)
    ))

    fig.add_trace(go.Scatter(
        x=df_plot.index,
        y=df_plot["MA21"],
        line=dict(width=1)
    ))

    fig.update_layout(
        height=400,
        margin=dict(l=5, r=5, t=5, b=5),
        xaxis_rangeslider_visible=False,
        plot_bgcolor="black",
        paper_bgcolor="black",
        font=dict(color="white"),
        showlegend=False
    )

    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=False)

    return fig

# =========================
# 🧠 IA
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
# RESTO (INALTERADO)
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
    if abs(price - ma21) > atr * 1.8:
        return False
    return True

def entrada_extra(df):
    price = df["close"].iloc[-1]
    ma21 = df["MA21"].iloc[-1]
    atr = df["ATR"].iloc[-1]
    score = score_ia(df)
    trend = tendencia_forte(df)
    pullback = abs(price - ma21) < atr * 0.9
    last = df["close"].iloc[-1]
    prev = df["close"].iloc[-2]
    if trend == "UP" and score >= 2 and pullback and last > prev:
        return "COMPRA"
    if trend == "DOWN" and score <= -2 and pullback and last < prev:
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

def horario_sistema():
    hora = datetime.now().hour
    dia = datetime.now().weekday()
    return {"operacao_liberada": hora >= 8 and dia < 5}

# =========================
# EXECUÇÃO
# =========================
if ligado:

    df = pegar_dados()

    if df is not None:

        df = indicadores(df)

        sinal_atual = sinal(df)
        preco = df["close"].iloc[-1]

        st.markdown("## 📊 PAINEL IA")

        # 🔥 GRÁFICO LIMPO
        st.plotly_chart(mostrar_grafico(df), use_container_width=True)

        st.write("Ativo:", ativo)
        st.write("Preço:", preco)
        st.write("Sinal:", sinal_atual)

else:
    st.warning("Robô desligado")
