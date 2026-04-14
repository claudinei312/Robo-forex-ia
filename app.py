# =========================
# 🧠 ESTRATÉGIA GBP/USD (NOVA - ORIGINAL SUA)
# =========================
def tendencia_forte_gbp(df):
    closes = df["close"].tail(10)
    alta = sum(closes.diff() > 0)
    baixa = sum(closes.diff() < 0)

    if alta >= 7:
        return "UP"
    elif baixa >= 7:
        return "DOWN"
    return "LATERAL"

def estrategia_gbpusd_nova(df):

    rsi = df["RSI"].iloc[-1]
    rsi_ant = df["RSI"].iloc[-2]

    ma21 = df["MA21"].iloc[-1]
    price = df["close"].iloc[-1]
    atr = df["ATR"].iloc[-1]

    trend = tendencia_forte_gbp(df)
    distancia = abs(price - ma21)

    if trend == "UP":
        if distancia > atr * 1.0:
            if rsi_ant < 50 and rsi > rsi_ant:
                if price > df["close"].iloc[-2]:
                    return "COMPRA"

    if trend == "DOWN":
        if distancia > atr * 1.0:
            if rsi_ant > 50 and rsi < rsi_ant:
                if price < df["close"].iloc[-2]:
                    return "VENDA"

    return "AGUARDAR"


# =========================
# 📊 BACKTEST GBP/USD (SEU ORIGINAL)
# =========================
def backtest_gbpusd(df):

    saldo = 1000
    risco = 0.02

    wins = 0
    losses = 0

    max_loss_seq = 0
    loss_seq = 0

    for i in range(50, len(df)-20):

        sub = df.iloc[:i]
        sinal = estrategia_gbpusd_nova(sub)

        if sinal == "AGUARDAR":
            continue

        entrada = sub["close"].iloc[-1]
        atr = sub["ATR"].iloc[-1]

        stop = atr * 1.2
        take = atr * 1.2

        resultado = None

        for j in range(i+1, i+20):

            high = df["high"].iloc[j]
            low = df["low"].iloc[j]

            if sinal == "COMPRA":
                if low <= entrada - stop:
                    resultado = -1
                    break
                if high >= entrada + take:
                    resultado = 1
                    break

            elif sinal == "VENDA":
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
            if loss_seq > max_loss_seq:
                max_loss_seq = loss_seq

    total = wins + losses
    winrate = (wins / total * 100) if total > 0 else 0

    return saldo, winrate, wins, losses, max_loss_seq
