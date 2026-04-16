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
import requests  # 🔥 ADICIONADO (NOTÍCIAS)

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
# 📰 NOTÍCIAS ECONÔMICAS (ADICIONADO)
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
# ESTRATÉGIA BASE
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
# BACKTEST SIMPLES
# =========================
def backtest_simples(df):

    wins = 0
    losses = 0

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

# =========================
# GBP COLAB
# =========================
def backtest_gbp_colab(df):

    saldo = 1000
    risco = 0.02

    wins = 0
    losses = 0

    max_loss_seq = 0
    loss_seq = 0

    df = df.tail(500)

    for i in range(50, len(df)-20):

        sub = df.iloc[:i]
        sig = sinal(sub)

        if sig == "AGUARDAR":
            continue

        entrada = sub["close"].iloc[-1]
        atr = sub["ATR"].iloc[-1]

        stop = atr * 1.2
        take = atr * 1.2

        resultado = None

        for j in range(i+1, i+20):

            high = df["high"].iloc[j]
            low = df["low"].iloc[j]

            if sig == "COMPRA":
                if low <= entrada - stop:
                    resultado = -1
                    break
                if high >= entrada + take:
                    resultado = 1
                    break

            elif sig == "VENDA":
                if high >= entrada + stop:
                    resultado = -1
                    break
                if low <= entrada - take:
                    resultado = 1
                    break

        if resultado is None:
            continue

        if resultado == 1:
            saldo += saldo * risco
            wins += 1
            loss_seq = 0
        else:
            saldo -= saldo * risco
            losses += 1
            loss_seq += 1
            max_loss_seq = max(max_loss_seq, loss_seq)

    total = wins + losses
    wr = (wins / total * 100) if total > 0 else 0

    return saldo, wr, wins, losses, max_loss_seq

# =========================
# USDJPY COLAB
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

def backtest_usdjpy_colab(df):

    saldo = 1000
    risco = 0.02

    wins = 0
    losses = 0

    max_loss_seq = 0
    loss_seq = 0

    df = df.tail(500)

    for i in range(50, len(df)-20):

        sub = df.iloc[:i]
        sig = estrategia_usdjpy(sub)

        if sig == "AGUARDAR":
            continue

        entrada = sub["close"].iloc[-1]
        atr = sub["ATR"].iloc[-1]

        stop = atr * 1.0
        take = atr * 1.2

        resultado = None

        for j in range(i+1, i+20):

            high = df["high"].iloc[j]
            low = df["low"].iloc[j]

            if sig == "COMPRA":
                if low <= entrada - stop:
                    resultado = -1
                    break
                if high >= entrada + take:
                    resultado = 1
                    break

            elif sig == "VENDA":
                if high >= entrada + stop:
                    resultado = -1
                    break
                if low <= entrada + take:
                    resultado = 1
                    break

        if resultado is None:
            continue

        if resultado == 1:
            saldo += saldo * risco
            wins += 1
            loss_seq = 0
        else:
            saldo -= saldo * risco
            losses += 1
            loss_seq += 1
            max_loss_seq = max(max_loss_seq, loss_seq)

    total = wins + losses
    wr = (wins / total * 100) if total > 0 else 0

    return saldo, wr, wins, losses, max_loss_seq

# =========================
# AUDUSD COLAB
# =========================
def estrategia_audusd(df):

    ma9 = df["MA9"].iloc[-1]
    ma21 = df["MA21"].iloc[-1]
    rsi = df["RSI"].iloc[-1]
    atr = df["ATR"].iloc[-1]

    price = df["close"].iloc[-1]

    high_prev = df["high"].iloc[-2]
    low_prev = df["low"].iloc[-2]

    ma21_ant = df["MA21"].iloc[-5]

    if abs(ma21 - ma21_ant) < atr * 0.3:
        return "AGUARDAR"

    tendencia_alta = ma9 > ma21
    tendencia_baixa = ma9 < ma21

    distancia = abs(price - ma9)

    if tendencia_alta:
        if 50 < rsi < 65:
            if distancia < atr * 0.6:
                if price > high_prev:
                    return "COMPRA"

    if tendencia_baixa:
        if 35 < rsi < 50:
            if distancia < atr * 0.25:
                if price < low_prev and price < ma21 and price < ma9:
                    return "VENDA"

    return "AGUARDAR"

def backtest_audusd_colab(df):

    saldo = 1000
    risco = 0.02

    wins = 0
    losses = 0

    max_loss_seq = 0
    loss_seq = 0

    df = df.tail(500)

    cooldown = 6

    for i in range(50, len(df)-20):

        if cooldown > 0:
            cooldown -= 1
            continue

        sub = df.iloc[:i]
        sig = estrategia_audusd(sub)

        if sig == "AGUARDAR":
            continue

        entrada = sub["close"].iloc[-1]
        atr = sub["ATR"].iloc[-1]

        stop = atr * 1.2
        take = atr * 1.4

        resultado = None

        for j in range(i+1, i+20):

            high = df["high"].iloc[j]
            low = df["low"].iloc[j]

            if sig == "COMPRA":
                if low <= entrada - stop:
                    resultado = -1
                    break
                if high >= entrada + take:
                    resultado = 1
                    break

            elif sig == "VENDA":
                if high >= entrada + stop:
                    resultado = -1
                    break
                if low <= entrada + take:
                    resultado = 1
                    break

        if resultado is None:
            continue

        cooldown = 6

        if resultado == 1:
            saldo += saldo * risco * 1.4
            wins += 1
            loss_seq = 0
        else:
            saldo -= saldo * risco
            losses += 1
            loss_seq += 1
            max_loss_seq = max(max_loss_seq, loss_seq)

    total = wins + losses
    wr = (wins / total * 100) if total > 0 else 0

    return saldo, wr, wins, losses, max_loss_seq

# =========================
# CONTROLADOR
# =========================
def rodar_backtest(ativo, df):

    if ativo == "GBP/USD":
        return backtest_gbp_colab(df)

    if ativo == "USD/JPY":
        return backtest_usdjpy_colab(df)

    if ativo == "AUD/USD":
        return backtest_audusd_colab(df)

    return backtest_simples(df)

# =========================
# EXECUÇÃO
# =========================
if ligado:

    status = horario_sistema()

    st.markdown("## 📊 PAINEL MULTI ATIVOS")

    # =========================
    # 📰 PAINEL DE NOTÍCIAS (ADICIONADO)
    # =========================
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
# 🚨 PAINEL DE ENTRADAS EM TEMPO REAL (NOVO)
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

    if sig == "COMPRA" or sig == "VENDA":

        st.success("🔥 ENTRADA DETECTADA")

        st.write("📌 Ativo:", ativo)
        st.write("⏰ Horário:", agora)
        st.write("📊 Tipo:", sig)
        st.write("💰 Preço:", preco)

        if st.session_state.get(f"alert_{ativo}") != sig:

            enviar_email(
                f"🚨 ALERTA DE ENTRADA {sig}",
                f"{ativo}\nTipo: {sig}\nPreço: {preco}\nHorário: {agora}"
            )

            st.session_state[f"alert_{ativo}"] = sig

    else:
        st.warning("⏳ Aguardando oportunidade...")
