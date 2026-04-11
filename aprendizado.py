import csv

def salvar_trade(rsi, tipo):
    with open("trades.csv", "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([rsi, tipo])

def analisar_erro(rsi):
    if rsi > 65:
        return "RSI muito alto"
    elif rsi < 35:
        return "RSI muito baixo"
    return "Mercado instável"
