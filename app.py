import streamlit as st
import pandas as pd
from twelvedata import TDClient
from ta.trend import SMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange
from datetime import datetime, time
import smtplib
from email.mime.text import MIMEText

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="🤖 Robô IA PRO v6", layout="centered")
st.title("🤖 Robô Forex IA PRO v6 FINAL")

ligado = st.toggle("🔌 Ligar Robô", value=True)

ativos = ["EUR/USD", "GBP/USD"]
ativo = st.selectbox("📊 Ativo", ativos)

API_KEY = st.secrets["API_KEY"]
EMAIL = st.secrets["EMAIL"]
SENHA = st.secrets["SENHA"]

td = TDClient(API_KEY)

# =========================
# MEMÓRIA
# =========================
if "posicao" not in st.session_state:
    st.session_state.posicao = None

if "historico" not in st.session_state:
    st.session_state.historico = []

if "erros" not in st.session_state:
    st.session_state.erros = []

if "parametros" not in st.session_state:
    st.session_state.parametros = {
        "rsi_compra": 55,
        "rsi_venda": 45
    }

if "sequencia" not in st.session_state:
    st.session_state.sequencia = []

# =========================
# EMAIL
# =========================
def enviar_email(msg):
    try:
        m = MIMEText(msg)
        m["Subject"] = "🤖 Robô Forex IA"
        m["From"] = EMAIL
        m["To"] = EMAIL
        s = smtplib.SMTP("smtp.gmail.com", 587)
        s.starttls()
        s.login(EMAIL, SENHA)
        s.sendmail(EMAIL, EMAIL, m.as_string())
        s.quit()
    except:
        pass

# =========================
# DADOS
# =========================
def pegar_dados():
    try:
        df = td.time_series(symbol=ativo, interval="5min", outputsize=300).as_pandas()
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
# ESTRATÉGIAS
# =========================
def tendencia(df):
    if df["MA9"].iloc[-1] > df["MA21"].iloc[-1] and df["RSI"].iloc[-1] > st.session_state.parametros["rsi_compra"]:
        return "COMPRA"
    if df["MA9"].iloc[-1] < df["MA21"].iloc[-1] and df["RSI"].iloc[-1] < st.session_state.parametros["rsi_venda"]:
        return "VENDA"
    return "AGUARDAR"

def price_action(df):
    suporte = df["low"].rolling(20).min().iloc[-1]
    resistencia = df["high"].rolling(20).max().iloc[-1]
    preco = df["close"].iloc[-1]

    if preco <= suporte * 1.001:
        return "COMPRA"
    if preco >= resistencia * 0.999:
        return "VENDA"
    return "AGUARDAR"

def rejeicao(df):
    c = df.iloc[-1]
    corpo = abs(c["close"] - c["open"])
    pavio_inf = c["open"] - c["low"]
    pavio_sup = c["high"] - c["open"]

    if pavio_inf > corpo * 2:
        return "COMPRA"
    if pavio_sup > corpo * 2:
        return "VENDA"
    return "AGUARDAR"

def macd(df):
    m = MACD(df["close"])
    if m.macd().iloc[-1] > m.macd_signal().iloc[-1]:
        return "COMPRA"
    if m.macd().iloc[-1] < m.macd_signal().iloc[-1]:
        return "VENDA"
    return "AGUARDAR"

# =========================
# IA ESCOLHE MELHOR ESTRATÉGIA
# =========================
def escolher_estrategia(df):

    estrategias = {
        "TENDENCIA": tendencia,
        "PRICE_ACTION": price_action,
        "REJEICAO": rejeicao,
        "MACD": macd
    }

    ranking = {}

    for nome, func in estrategias.items():
        wins = 0
        total = 0

        for i in range(50, len(df)-1):
            sub = df.iloc[:i]
            sinal = func(sub)

            if sinal == "AGUARDAR":
                continue

            preco = sub["close"].iloc[-1]
            prox = df["close"].iloc[i+1]

            total += 1

            if (sinal == "COMPRA" and prox > preco) or (sinal == "VENDA" and prox < preco):
                wins += 1

        ranking[nome] = wins / total if total else 0

    melhor = max(ranking, key=ranking.get)
    return melhor, ranking

# =========================
# BACKTEST
# =========================
def backtest(df):
    wins = 0
    losses = 0

    for i in range(50, len(df)-1):
        sub = df.iloc[:i]
        melhor, _ = escolher_estrategia(sub)

        mapa = {
            "TENDENCIA": tendencia,
            "PRICE_ACTION": price_action,
            "REJEICAO": rejeicao,
            "MACD": macd
        }

        sinal = mapa[melhor](sub)

        if sinal == "AGUARDAR":
            continue

        preco = sub["close"].iloc[-1]
        prox = df["close"].iloc[i+1]

        if (sinal == "COMPRA" and prox > preco) or (sinal == "VENDA" and prox < preco):
            wins += 1
        else:
            losses += 1
            st.session_state.erros.append({
                "tipo": sinal,
                "preco": preco
            })

    total = wins + losses
    return wins, losses, (wins/total*100 if total else 0)

# =========================
# EXECUÇÃO
# =========================
if ligado:

    df = pegar_dados()

    if df is None:
        st.write("Carregando...")
    else:

        df = indicadores(df)

        melhor, ranking = escolher_estrategia(df)

        mapa = {
            "TENDENCIA": tendencia,
            "PRICE_ACTION": price_action,
            "REJEICAO": rejeicao,
            "MACD": macd
        }

        sinal = mapa[melhor](df)
        preco = df["close"].iloc[-1]
        atr = df["ATR"].iloc[-1]

        st.markdown("## 🧠 IA Estratégica")
        st.write("Estratégia atual:", melhor)

        for k,v in ranking.items():
            st.write(f"{k}: {v:.2f}")

        st.markdown("## 📊 Mercado")
        st.write("Preço:", preco)
        st.write("Sinal:", sinal)

        if sinal != "AGUARDAR" and st.session_state.posicao is None:

            sl = preco - atr if sinal == "COMPRA" else preco + atr
            tp = preco + atr*2 if sinal == "COMPRA" else preco - atr*2

            st.session_state.posicao = {
                "tipo": sinal,
                "entrada": preco,
                "tp": tp,
                "sl": sl
            }

            enviar_email(f"{sinal} {ativo} {preco}")

        if st.session_state.posicao:

            st.markdown("## 📌 Operação ativa")
            st.write(st.session_state.posicao)

            atual = preco

            if st.session_state.posicao["tipo"] == "COMPRA":
                if atual <= st.session_state.posicao["sl"]:
                    resultado = "LOSS"
                elif atual >= st.session_state.posicao["tp"]:
                    resultado = "WIN"
                else:
                    resultado = None

            else:
                if atual >= st.session_state.posicao["sl"]:
                    resultado = "LOSS"
                elif atual <= st.session_state.posicao["tp"]:
                    resultado = "WIN"
                else:
                    resultado = None

            if resultado:
                st.session_state.sequencia.append(resultado)
                st.write("Resultado:", resultado)
                st.session_state.posicao = None

        st.markdown("## 📊 Backtest")
        w, l, wr = backtest(df)
        st.write(f"Wins: {w} | Losses: {l} | Winrate: {wr:.2f}%")

else:
    st.warning("Robô desligado")
