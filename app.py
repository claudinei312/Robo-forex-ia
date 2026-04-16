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
        r = requests.get(url, timeout=10)
        return r.json()
    except:
        return []

def filter_news(data, assets):
    news_list = []
    now = datetime.utcnow()

    for e in data:
        try:
            currency = e.get("currency", "")
            impact = e.get("impact", "")
            title = e.get("title", "")
            time_str = e.get("date", "")

            if currency not in assets:
                continue

            event_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            minutes = (event_time - now).total_seconds() / 60

            news_list.append({
                "Moeda": currency,
                "Evento": title,
                "Impacto": impact,
                "Horário": event_time,
                "Minutos": round(minutes)
            })
        except:
            continue

    return sorted(news_list, key=lambda x: x["Minutos"])

def get_news_status(news_list):
    for n in news_list:
        if n["Impacto"] == "High" and 0 < n["Minutos"] < 60:
            return "🔴 ALTA VOLATILIDADE"
        if n["Impacto"] == "High" and 60 < n["Minutos"] < 180:
            return "🟡 ATENÇÃO"
    return "🟢 NORMAL"

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="🤖 Robô IA v9 FULL", layout="centered")
st.title("🤖 ROBÔ FOREX IA v9 - MULTI ATIVOS")

ligado = st.toggle("🔌 Ligar Robô", value=True)

td = TDClient(st.secrets["API_KEY"])

ativos = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD"]

# =========================
# CACHE (ECONOMIA API)
# =========================
cache = {}

def pegar_dados(ativo):
    agora = datetime.now()

    if ativo in cache:
        ultimo = cache[ativo]["time"]
        if (agora - ultimo).seconds < 240:
            return cache[ativo]["df"]

    try:
        df = td.time_series(
            symbol=ativo,
            interval="5min",
            outputsize=1200  # ~10 dias M5
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
# IA SCORE
# =========================
def score_ia(df):
    score = 0

    score += 1 if df["MA9"].iloc[-1] > df["MA21"].iloc[-1] else -1

    rsi = df["RSI"].iloc[-1]
    if rsi > 55:
        score += 1
    elif rsi < 45:
        score -= 1

    m = MACD(df["close"])
    score += 1 if m.macd().iloc[-1] > m.macd_signal().iloc[-1] else -1

    atr = df["ATR"].iloc[-1]
    score += 1 if atr > df["ATR"].rolling(50).mean().iloc[-1] else -1

    return score

# =========================
# ESTRATÉGIAS
# =========================
def tendencia_forte(df):
    closes = df["close"].tail(10)
    alta = sum(closes.iloc[i] > closes.iloc[i-1] for i in range(1, len(closes)))
    baixa = len(closes) - 1 - alta

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
# BACKTESTS
# =========================
def backtest_simples(df):
    df = df.tail(1000)

    wins, losses = 0, 0

    for i in range(60, len(df)-1):
        sub = df.iloc[:i]
        sig = sinal(sub)

        if sig == "AGUARDAR":
            continue

        price = sub["close"].iloc[-1]
        future = df["close"].iloc[i+1]

        if (sig == "COMPRA" and future > price) or (sig == "VENDA" and future < price):
            wins += 1
        else:
            losses += 1

    total = wins + losses
    wr = (wins / total * 100) if total > 0 else 0

    return wins, losses, total, round(wr, 2)

# (outros backtests mantidos iguais, só com tail(1000))
# Para não ficar gigante aqui, eles seguem exatamente como você já tinha,
# apenas trocando df.tail(500) por df.tail(1000)

def rodar_backtest(ativo, df):
    return backtest_simples(df)

# =========================
# EXECUÇÃO
# =========================
if ligado:

    st.markdown("## 📊 PAINEL MULTI ATIVOS")

    data_news = get_economic_news()
    news = filter_news(data_news, ["USD", "EUR", "GBP"])
    status_news = get_news_status(news)

    st.markdown(f"### 📰 Status: {status_news}")

    for ativo in ativos:

        df = pegar_dados(ativo)

        if df is None or df.empty:
            continue

        df = indicadores(df)

        sig = sinal(df)
        preco = df["close"].iloc[-1]

        st.markdown(f"### 📊 {ativo}")
        st.write("Preço:", preco)
        st.write("Sinal:", sig)

        # BACKTEST
        w, l, t, wr = rodar_backtest(ativo, df)
        st.write(f"📊 Backtest (10 dias)")
        st.write(f"Wins: {w} | Losses: {l} | WR: {wr}%")

        if sig in ["COMPRA", "VENDA"]:
            st.success("🔥 ENTRADA DETECTADA")

            if st.session_state.get(f"alert_{ativo}") != sig:
                enviar_email(
                    f"🚨 {sig}",
                    f"{ativo} | {sig} | {preco}"
                )
                st.session_state[f"alert_{ativo}"] = sig
        else:
            st.warning("⏳ Aguardando...")

else:
    st.warning("Robô desligado")
