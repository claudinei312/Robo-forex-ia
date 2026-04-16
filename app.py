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


# =========================
# EMAIL
# =========================
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
# NOTÍCIAS
# =========================
def get_economic_news():
    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    try:
        return requests.get(url, timeout=10).json()
    except:
        return []


def filter_news(data, assets):
    news_list = []
    now = datetime.utcnow()

    assets = set(assets)

    for e in data:
        try:
            currency = e.get("currency", "").strip().upper()

            if currency not in assets:
                continue

            event_time = datetime.strptime(e.get("date", ""), "%Y-%m-%d %H:%M:%S")
            minutes = (event_time - now).total_seconds() / 60

            news_list.append({
                "Moeda": currency,
                "Evento": e.get("title", ""),
                "Impacto": e.get("impact", ""),
                "Horário": event_time,
                "Minutos": round(minutes)
            })

        except:
            continue

    return sorted(news_list, key=lambda x: x["Minutos"])


# =========================
# CONFIG
# =========================
st.set_page_config(page_title="🤖 ROBÔ IA MULTI-STRATEGY", layout="centered")
st.title("🤖 ROBÔ IA - STRATEGY SWITCHING")

ligado = st.toggle("🔌 Ligar Robô", value=True)

td = TDClient(st.secrets["API_KEY"])

ativos = ["EUR/USD", "USD/JPY", "AUD/USD"]


# =========================
# DADOS
# =========================
def pegar_dados(ativo):
    try:
        df = td.time_series(
            symbol=ativo,
            interval="5min",
            outputsize=500
        ).as_pandas()

        df = df[::-1].reset_index(drop=True)

        for c in ["open", "high", "low", "close"]:
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
# IA - ESCOLHA DE ESTRATÉGIA
# =========================
def escolher_estrategia(df):

    ma9 = df["MA9"].iloc[-1]
    ma21 = df["MA21"].iloc[-1]
    rsi = df["RSI"].iloc[-1]
    atr = df["ATR"].iloc[-1]
    price = df["close"].iloc[-1]

    tendencia = abs(ma9 - ma21)
    volatilidade = atr / price

    if tendencia > atr * 0.5:
        return "TREND"

    if 40 < rsi < 60:
        return "REVERSAO"

    if volatilidade > 0.003:
        return "BREAKOUT"

    return "TREND"


# =========================
# ESTRATÉGIAS
# =========================
def estrategia_trend(df):

    if df["MA9"].iloc[-1] > df["MA21"].iloc[-1]:
        return "COMPRA"
    if df["MA9"].iloc[-1] < df["MA21"].iloc[-1]:
        return "VENDA"

    return "AGUARDAR"


def estrategia_reversao(df):

    rsi = df["RSI"].iloc[-1]

    if rsi < 30:
        return "COMPRA"
    if rsi > 70:
        return "VENDA"

    return "AGUARDAR"


def estrategia_breakout(df):

    atr = df["ATR"].iloc[-1]
    close = df["close"].iloc[-1]

    high_prev = df["high"].iloc[-2]
    low_prev = df["low"].iloc[-2]

    if close > high_prev + atr:
        return "COMPRA"
    if close < low_prev - atr:
        return "VENDA"

    return "AGUARDAR"


# =========================
# SINAL FINAL (IA)
# =========================
def sinal(df):

    modo = escolher_estrategia(df)

    if modo == "TREND":
        return estrategia_trend(df)

    if modo == "REVERSAO":
        return estrategia_reversao(df)

    if modo == "BREAKOUT":
        return estrategia_breakout(df)

    return "AGUARDAR"


# =========================
# BACKTEST REALISTA
# =========================
def backtest_realista(df):

    wins = 0
    losses = 0

    sl_mult = 1.0
    tp_mult = 1.5
    max_bars = 20

    for i in range(60, len(df) - max_bars):

        sub = df.iloc[:i]
        sig = sinal(sub)

        if sig == "AGUARDAR":
            continue

        entry = df["open"].iloc[i]
        atr = sub["ATR"].iloc[-1]

        sl = atr * sl_mult
        tp = atr * tp_mult

        result = None

        for j in range(i + 1, i + max_bars):

            high = df["high"].iloc[j]
            low = df["low"].iloc[j]

            if sig == "COMPRA":
                if low <= entry - sl:
                    result = -1
                    break
                if high >= entry + tp:
                    result = 1
                    break

            elif sig == "VENDA":
                if high >= entry + sl:
                    result = -1
                    break
                if low <= entry + tp:
                    result = 1
                    break

        if result == 1:
            wins += 1
        elif result == -1:
            losses += 1

    total = wins + losses
    wr = (wins / total * 100) if total > 0 else 0

    return wins, losses, total, round(wr, 2)


# =========================
# BACKTEST CONTROL
# =========================
def rodar_backtest(df):
    return backtest_realista(df)


# =========================
# EXECUÇÃO
# =========================
if ligado:

    st.markdown("## 📊 ROBÔ IA MULTI-ESTRATÉGIA")

    assets_news = ["USD", "EUR"]

    news = filter_news(get_economic_news(), assets_news)

    st.markdown("## 📰 NOTÍCIAS")
    st.dataframe(pd.DataFrame(news))

    ranking = {}

    for ativo in ativos:

        df = pegar_dados(ativo)
        if df is None:
            continue

        df = indicadores(df)

        sig = sinal(df)
        preco = df["close"].iloc[-1]

        st.markdown(f"### {ativo}")
        st.write("Preço:", preco)
        st.write("Sinal:", sig)

        w, l, t, wr = rodar_backtest(df)

        st.write(f"Wins: {w} Losses: {l} Winrate: {wr}%")

        ranking[ativo] = wr

    st.markdown("## 🏆 Ranking")
    st.write(ranking)

else:
    st.warning("Robô desligado")
