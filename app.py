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

# 🔥 FIX: AUTO REFRESH
from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=5000, key="refresh")

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

# 🔥 FIX SESSION STATE ALERTAS
if "alerts" not in st.session_state:
    st.session_state.alerts = {}


# =========================
# DADOS
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

        df = df.dropna()

        if df.empty:
            return None

        return df

    except Exception as e:
        st.error(f"Erro API {ativo}: {e}")
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
# EXECUÇÃO
# =========================
if ligado:

    status = horario_sistema()

    st.markdown("## 📊 PAINEL MULTI ATIVOS")

    # NOTÍCIAS
    st.markdown("## 📰 NOTÍCIAS ECONÔMICAS")

    assets_news = ["USD", "EUR", "GBP"]

    data_news = get_economic_news()
    news = filter_news(data_news, assets_news)
    status_news = get_news_status(news)

    st.markdown(f"### Status do Mercado: {status_news}")

    if news:
        st.dataframe(pd.DataFrame(news), use_container_width=True)
    else:
        st.info("Sem notícias relevantes no momento.")

    ranking = {}

    for ativo in ativos:

        df = pegar_dados(ativo)

        if df is None:
            continue

        df = indicadores(df)

        sig = sinal(df)
        preco = df["close"].iloc[-1]

        st.markdown(f"### 📊 {ativo}")
        st.write("Preço:", preco)
        st.write("Sinal:", sig)

        if status["operacao_liberada"]:
            if sig == "COMPRA":
                enviar_email("📈 COMPRA", f"{ativo} - {preco}")
            if sig == "VENDA":
                enviar_email("📉 VENDA", f"{ativo} - {preco}")

        result = rodar_backtest(ativo, df)

        if ativo in ["GBP/USD", "USD/JPY", "AUD/USD"]:
            saldo, wr, w, l, max_ls = result
            st.write(f"Wins: {w}  Losses: {l}  Winrate: {round(wr,1)}")
            ranking[ativo] = wr
        else:
            w, l, t, wr = result
            st.write(f"Wins: {w}  Losses: {l}  Winrate: {round(wr,1)}")
            ranking[ativo] = wr

    melhor = max(ranking, key=ranking.get) if ranking else "Nenhum ativo"

    st.markdown("## 🏆 Ranking")
    st.write(ranking)
    st.write("Melhor ativo:", melhor)

else:
    st.warning("Robô desligado")


# =========================
# ENTRADAS EM TEMPO REAL
# =========================

st.markdown("## 🚨 ENTRADAS EM TEMPO REAL")

for ativo in ativos:

    df = pegar_dados(ativo)

    if df is None:
        continue

    df = indicadores(df)

    sig = sinal(df)
    preco = df["close"].iloc[-1]
    agora = datetime.now().strftime("%H:%M:%S")

    st.markdown(f"### 📍 {ativo}")

    if sig in ["COMPRA", "VENDA"]:

        st.success("🔥 ENTRADA DETECTADA")

        st.write("📌 Ativo:", ativo)
        st.write("⏰ Horário:", agora)
        st.write("📊 Tipo:", sig)
        st.write("💰 Preço:", preco)

        if st.session_state.alerts.get(ativo) != sig:

            enviar_email(
                f"🚨 ALERTA {sig}",
                f"{ativo}\n{sig}\n{preco}\n{agora}"
            )

            st.session_state.alerts[ativo] = sig

    else:
        st.warning("⏳ Aguardando oportunidade...")
