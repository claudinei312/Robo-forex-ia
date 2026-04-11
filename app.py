import streamlit as st
import pandas as pd
from twelvedata import TDClient
from ta.trend import SMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange
from datetime import datetime
import random

# =========================
# 🟩 CAMADA 1 - CONFIG
# =========================
st.set_page_config(page_title="🤖 Robô IA v9 FULL", layout="centered")
st.title("🤖 ROBÔ FOREX IA v9 - COMPLETO")

ligado = st.toggle("🔌 Ligar Robô", value=True)
ativo = st.selectbox("📊 Ativo", ["EUR/USD", "GBP/USD"])

td = TDClient(st.secrets["API_KEY"])

# =========================
# 🟨 CAMADA 2 - MEMÓRIA IA
# =========================
if "posicao" not in st.session_state:
    st.session_state.posicao = None

if "erros" not in st.session_state:
    st.session_state.erros = []

if "ranking_global" not in st.session_state:
    st.session_state.ranking_global = {
        "TENDENCIA": 1.0,
        "PRICE_ACTION": 1.0,
        "REJEICAO": 1.0,
        "MACD": 1.0
    }

if "sequencia" not in st.session_state:
    st.session_state.sequencia = []

# =========================
# 🟥 CAMADA 8 - FASE DO MERCADO (NOVO)
# =========================
def fase_mercado():
    hora = datetime.now().hour
    dia = datetime.now().weekday()

    if dia >= 5:
        return "TREINO"  # fim de semana

    if hora < 6:
        return "INATIVO"

    if 6 <= hora < 8:
        return "BACKTEST"

    if hora >= 8:
        return "OPERACAO"

    return "PROTECAO"

# =========================
# 🟦 CAMADA 3 - DADOS
# =========================
def pegar_dados():
    try:
        df = td.time_series(symbol=ativo, interval="5min", outputsize=250).as_pandas()
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
# 🟨 CAMADA 4 - ESTRATÉGIAS
# =========================
def tendencia(df):
    rsi = df["RSI"].iloc[-1]
    if df["MA9"].iloc[-1] > df["MA21"].iloc[-1] and rsi > 55:
        return "COMPRA"
    if df["MA9"].iloc[-1] < df["MA21"].iloc[-1] and rsi < 45:
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

    if (c["open"] - c["low"]) > corpo * 2:
        return "COMPRA"
    if (c["high"] - c["open"]) > corpo * 2:
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
# 🟪 CAMADA 9 - IA AVANÇADA (NOVO)
# =========================
def ajustar_rsi(df):
    volatilidade = df["ATR"].iloc[-1]
    if volatilidade > 0.001:
        return 60, 40
    return 55, 45

def score_mercado(df):
    atr = df["ATR"].iloc[-1]
    if atr > 0.002:
        return "FORTE"
    if atr < 0.0005:
        return "FRACO"
    return "NORMAL"

def atualizar_pesos(estrategia, resultado):
    if resultado == "LOSS":
        st.session_state.ranking_global[estrategia] *= 0.95
    else:
        st.session_state.ranking_global[estrategia] *= 1.02

# =========================
# 🧠 IA ESCOLHE ESTRATÉGIA
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

        for i in range(40, len(df)-1):
            sub = df.iloc[:i]
            sinal = func(sub)

            if sinal == "AGUARDAR":
                continue

            preco = sub["close"].iloc[-1]
            prox = df["close"].iloc[i+1]

            total += 1

            if (sinal == "COMPRA" and prox > preco) or (sinal == "VENDA" and prox < preco):
                wins += 1

        base = wins / total if total > 0 else 0
        ranking[nome] = base * st.session_state.ranking_global[nome]

    melhor = max(ranking, key=ranking.get)

    return melhor, ranking

# =========================
# 🟫 BACKTEST
# =========================
def backtest(df):

    wins = 0
    losses = 0

    for i in range(40, len(df)-1):

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
            atualizar_pesos(melhor, "WIN")
        else:
            losses += 1
            atualizar_pesos(melhor, "LOSS")

    total = wins + losses
    return wins, losses, (wins/total*100 if total else 0)

# =========================
# 🟦 EXECUÇÃO PRINCIPAL
# =========================
if ligado:

    df = pegar_dados()

    if df is not None:

        df = indicadores(df)

        fase = fase_mercado()

        rsi_compra, rsi_venda = ajustar_rsi(df)

        melhor, ranking = escolher_estrategia(df)

        mapa = {
            "TENDENCIA": tendencia,
            "PRICE_ACTION": price_action,
            "REJEICAO": rejeicao,
            "MACD": macd
        }

        sinal = mapa[melhor](df)
        preco = df["close"].iloc[-1]

        # =========================
        # 🛑 CONTROLE DE FASE
        # =========================
        if fase != "OPERACAO":
            sinal = "AGUARDAR"

        # =========================
        # 📊 PAINEL
        # =========================
        st.markdown("## 📊 PAINEL IA COMPLETO")

        st.write("📊 Ativo:", ativo)
        st.write("💰 Preço:", preco)
        st.write("🧠 Estratégia:", melhor)
        st.write("📌 Fase:", fase)
        st.write("📢 Sinal:", sinal)

        st.markdown("## 📈 Ranking IA")
        for k,v in ranking.items():
            st.write(k, round(v,3))

        st.markdown("## 🧠 IA GLOBAL PESOS")
        st.write(st.session_state.ranking_global)

        # =========================
        # 📌 OPERAÇÃO
        # =========================
        atr = df["ATR"].iloc[-1]

        if sinal != "AGUARDAR" and st.session_state.posicao is None:

            st.session_state.posicao = {
                "tipo": sinal,
                "entrada": preco,
                "tp": preco + atr*2 if sinal == "COMPRA" else preco - atr*2,
                "sl": preco - atr if sinal == "COMPRA" else preco + atr
            }

        st.markdown("## 📌 OPERAÇÃO")

        if st.session_state.posicao:
            st.write(st.session_state.posicao)

        # =========================
        # 📊 BACKTEST
        # =========================
        w,l,wr = backtest(df)

        st.markdown("## 📊 BACKTEST")
        st.write("Wins:", w)
        st.write("Losses:", l)
        st.write("Winrate:", round(wr,2))

else:
    st.warning("Robô desligado")
