import csv
from datetime import datetime

def salvar_trade(rsi, tipo):
    with open("trades.csv", "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([datetime.now(), rsi, tipo])


def analisar_erro(rsi):
    if rsi > 65:
        return "RSI alto → risco de reversão"
    elif rsi < 35:
        return "RSI baixo → possível sobrevenda"
    return "Mercado neutro"
