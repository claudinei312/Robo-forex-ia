# =========================
# IMPORTS
# =========================
import pandas as pd
from twelvedata import TDClient
from ta.trend import SMAIndicator
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange

# =========================
# API
# =========================
API_KEY = "SUA_API_AQUI"
td = TDClient(apikey=API_KEY)

# =========================
# DADOS
# =========================
def pegar_dados(ativo):
    df = td.time_series(
        symbol=ativo,
        interval="15min",
        outputsize=5000
    ).as_pandas()

    df = df[::-1].reset_index(drop=True)

    for c in ["open", "high", "low", "close"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    return df.dropna()

# =========================
# INDICADORES
# =========================
def indicadores(df):
    df["MA9"] = SMAIndicator(df["close"], 9).sma_indicator()
    df["MA21"] = SMAIndicator(df["close"], 21).sma_indicator()
    df["RSI"] = RSIIndicator(df["close"], 14).rsi()
    df["ATR"] = AverageTrueRange(df["high"], df["low"], df["close"], 14).average_true_range()
    return df

# ==========================================================
# 🟢 AUD/USD ESTRATÉGIA (NOVO – NÃO ALTERA OUTROS ATIVOS)
# ==========================================================
def estrategia_audusd(df):

    ma9 = df["MA9"].iloc[-1]
    ma21 = df["MA21"].iloc[-1]
    rsi = df["RSI"].iloc[-1]
    atr = df["ATR"].iloc[-1]

    price = df["close"].iloc[-1]

    high_prev = df["high"].iloc[-2]
    low_prev = df["low"].iloc[-2]

    ma21_ant = df["MA21"].iloc[-5]

    # filtro mercado lateral
    if abs(ma21 - ma21_ant) < atr * 0.3:
        return "AGUARDAR", "sem tendencia"

    tendencia_alta = ma9 > ma21
    tendencia_baixa = ma9 < ma21

    distancia = abs(price - ma9)

    # COMPRA
    if tendencia_alta:
        if 50 < rsi < 65:
            if distancia < atr * 0.6:
                if price > high_prev:
                    return "COMPRA", "rompimento forte"

    # VENDA
    if tendencia_baixa:
        if 35 < rsi < 50:
            if distancia < atr * 0.25:
                if price < low_prev and price < ma21 and price < ma9:
                    return "VENDA", "rompimento forte"

    return "AGUARDAR", "sem sinal"

# =========================
# 📊 AUD/USD BACKTEST COLAB PADRÃO
# =========================
def backtest_audusd_colab(df):

    df = df.tail(500)

    saldo = 1000
    risco = 0.02

    wins = 0
    losses = 0

    cooldown = 6

    max_loss_seq = 0
    loss_seq = 0

    for i in range(50, len(df) - 20):

        if cooldown > 0:
            cooldown -= 1
            continue

        sub = df.iloc[:i]
        sig, motivo = estrategia_audusd(sub)

        if sig == "AGUARDAR":
            continue

        entrada = sub["close"].iloc[-1]
        atr = sub["ATR"].iloc[-1]

        stop = atr * 1.2
        take = atr * 1.4

        resultado = None

        for j in range(i + 1, i + 20):

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
    winrate = (wins / total * 100) if total > 0 else 0

    return saldo, winrate, wins, losses, max_loss_seq

# =========================
# 🚀 CONTROLADOR DE BACKTESTS
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
# 📊 BACKTEST SIMPLES (OUTROS ATIVOS)
# =========================
def backtest_simples(df):

    wins = 0
    losses = 0

    for i in range(60, len(df) - 1):

        sub = df.iloc[:i]
        # sinal genérico (mantido do seu robô)
        price = sub["close"].iloc[-1]
        future = df["close"].iloc[i + 1]

        if future > price:
            wins += 1
        else:
            losses += 1

    total = wins + losses
    wr = (wins / total * 100) if total > 0 else 0

    return wins, losses, total, round(wr, 2)

# =========================
# ⚠️ PLACEHOLDERS (mantém compatibilidade)
# =========================
def backtest_gbp_colab(df):
    return 0, 0, 0, 0, 0

def backtest_usdjpy_colab(df):
    return 0, 0, 0, 0, 0
