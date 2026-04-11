def prever(rsi, ma9, ma21, preco):

    # IA inicial (regra inteligente)
    score = 0

    if rsi > 50:
        score += 1

    if ma9 > ma21:
        score += 1

    if score >= 2:
        return 1  # aprova entrada

    return 0  # bloqueia
