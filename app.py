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
st.title("🤖 ROBÔ FOREX IA v9 - MULTI ATIVOS")

ligado = st.toggle("🔌 Ligar Robô", value=True)

td = TDClient(st.secrets["API_KEY"])

# 🔥 AGORA MULTI-ATIVOS
ativos = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD"]

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
            df = pegar_dados(a)
            df = indicadores(df)
            ranking[a] = score_ia(df)
        except:
            ranking[a] = 0

    melhor = max(ranking, key=ranking.get)
    return ranking, melhor

# =========================
# 🟦 DADOS
# =========================
def pegar_dados(ativo):
    try:
        df = td.time_series(
            symbol=ativo,
            interval="15min",
            outputsize=500
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
# 📈 GRÁFICO
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

    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot["MA9"], line=dict(width=1)))
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot["MA21"], line=dict(width=1)))

    fig.update_layout(
        height=350,
        margin=dict(l=5, r=5, t=5, b=5),
        xaxis_rangeslider_visible=False,
        plot_bgcolor="black",
        paper_bgcolor="black",
        font=dict(color="white"),
        showlegend=False
    )

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
# ESTRATÉGIA
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
# HORÁRIO
# =========================
def horario_sistema():
    hora = datetime.now().hour
    dia = datetime.now().weekday()
    return {"operacao_liberada": hora >= 8 and dia < 5}

# =========================
# BACKTEST (MULTI ATIVOS)
# =========================
def backtest(df):

    wins = 0
    losses = 0

    for i in range(60, len(df) - 1):

        sub = df.iloc[:i]
        sig = sinal(sub)

        if sig == "AGUARDAR":
            continue

        price = sub["close"].iloc[-1]
        next_price = df["close"].iloc[i + 1]

        if (sig == "COMPRA" and next_price > price) or (sig == "VENDA" and next_price < price):
            wins += 1
        else:
            losses += 1

    total = wins + losses
    return wins, losses, (wins / total * 100 if total else 0)

# =========================
# EXECUÇÃO
# =========================
if ligado:

    status = horario_sistema()

    st.markdown("## 📊 PAINEL MULTI ATIVOS")

    ranking, melhor = ranking_ativos()

    for ativo in ativos:

        df = pegar_dados(ativo)

        if df is None:
            continue

        df = indicadores(df)

        sig = sinal(df)
        preco = df["close"].iloc[-1]

        st.markdown(f"### 📊 {ativo}")

        st.plotly_chart(mostrar_grafico(df), use_container_width=True)

        st.write("Preço:", preco)
        st.write("Sinal:", sig)

        # EMAIL
        if status["operacao_liberada"]:
            if sig == "COMPRA":
                enviar_email("COMPRA", f"{ativo} - {preco}")
            if sig == "VENDA":
                enviar_email("VENDA", f"{ativo} - {preco}")

        w, l, wr = backtest(df)

        st.write("Backtest:", w, l, round(wr,2), "%")

    st.markdown("## 📰 Notícias")
    st.write(noticias())

    st.markdown("## 🏆 Ranking")
    st.write(ranking)
    st.write("Melhor:", melhor)

else:
    st.warning("Robô desligado")
