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
# CONFIG
# =========================
st.set_page_config(page_title="🤖 Robô IA v9 FULL", layout="centered")
st.title("🤖 ROBÔ FOREX IA v9 - MULTI ATIVOS")

ligado = st.toggle("🔌 Ligar Robô", value=True)

td = TDClient(st.secrets["API_KEY"])

ativos = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD"]

# =========================
# 📰 NOTÍCIAS PROFISSIONAL
# =========================
def pegar_noticias():

    try:
        url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
        data = requests.get(url).json()

        noticias = []

        for n in data:
            noticias.append({
                "moeda": n.get("currency"),
                "impacto": n.get("impact"),
                "titulo": n.get("title"),
                "hora": n.get("time")
            })

        return noticias

    except:
        return []

def filtro_noticias(ativo):

    noticias = pegar_noticias()

    moedas = ativo.split("/")

    risco = "LIBERADO"

    for n in noticias:

        if n["moeda"] in moedas:

            if "High" in str(n["impacto"]):
                return "BLOQUEADO 🔴", n["titulo"]

            elif "Medium" in str(n["impacto"]):
                risco = "ATENÇÃO 🟡"

    return risco, None

# =========================
# DADOS
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
# ESTRATÉGIA BASE (SEM ALTERAÇÃO)
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
import requests  # ✅ ADICIONADO

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
# CONFIG
# =========================
st.set_page_config(page_title="🤖 Robô IA v9 FULL", layout="centered")
st.title("🤖 ROBÔ FOREX IA v9 - MULTI ATIVOS")

ligado = st.toggle("🔌 Ligar Robô", value=True)

td = TDClient(st.secrets["API_KEY"])

ativos = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD"]

# =========================
# 📰 NOTÍCIAS (NOVO)
# =========================
def pegar_noticias():

    try:
        url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
        data = requests.get(url).json()

        noticias = []

        for n in data:
            noticias.append({
                "moeda": n.get("currency"),
                "impacto": n.get("impact"),
                "titulo": n.get("title"),
                "hora": n.get("time")
            })

        return noticias

    except:
        return []

def filtro_noticias(ativo):

    noticias = pegar_noticias()

    moedas = ativo.split("/")

    risco = "LIBERADO"

    for n in noticias:

        if n["moeda"] in moedas:

            if "High" in str(n["impacto"]):
                return "BLOQUEADO 🔴", n["titulo"]

            elif "Medium" in str(n["impacto"]):
                risco = "ATENÇÃO 🟡"

    return risco, None

# =========================
# DADOS
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
# ESTRATÉGIA BASE (INALTERADA)
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

    ranking = {}

    for ativo in ativos:

        df = pegar_dados(ativo)

        if df is None:
            continue

        df = indicadores(df)

        sig = sinal(df)
        preco = df["close"].iloc[-1]

        # 📰 NOTÍCIAS (APENAS ADIÇÃO)
        status_noticia, motivo = filtro_noticias(ativo)

        st.markdown(f"### 📊 {ativo}")
        st.write("Preço:", preco)
        st.write("Sinal:", sig)
        st.write("Notícias:", status_noticia)

        if motivo:
            st.warning(f"⚠️ {motivo}")

        # 🚫 BLOQUEIO
        if status_noticia == "BLOQUEADO 🔴":
            sig = "AGUARDAR"

        if status["operacao_liberada"]:
            if sig == "COMPRA":
                enviar_email("📈 COMPRA", f"{ativo} - {preco}")
            if sig == "VENDA":
                enviar_email("📉 VENDA", f"{ativo} - {preco}")

        ranking[ativo] = score_ia(df)

    melhor = max(ranking, key=ranking.get)

    st.markdown("## 🏆 Ranking")
    st.write(ranking)
    st.write("Melhor ativo:", melhor)

else:
    st.warning("Robô desligado")
