# =========================
# 🧪 BACKTEST CORRIGIDO (IGUAL 70%)
# =========================

st.markdown("## 🧪 BACKTEST MANUAL (ESTRATÉGIA REAL 70%)")

col1, col2 = st.columns(2)

def backtest_real(df):

    wins = 0
    losses = 0

    for i in range(60, len(df) - 1):

        sub = df.iloc[:i]

        # 🔥 AGORA USA A ESTRATÉGIA REAL (NÃO MAIS SIMPLIFICADA)
        sig = sinal(sub)

        if sig == "AGUARDAR":
            continue

        price = sub["close"].iloc[-1]
        next_price = df["close"].iloc[i + 1]

        if (sig == "COMPRA" and next_price > price) or (sig == "VENDA" and next_price < price):
            wins += 1
        else:
            losses += 1

    total = wins + losses
    wr = (wins / total * 100) if total else 0

    return wins, losses, wr


def filtrar_semana(df):
    df = df.copy()
    df["time"] = pd.to_datetime(df.index)
    df["weekday"] = df["time"].dt.weekday
    return df[df["weekday"] < 5]


with col1:
    if st.button("📊 Backtest Última Semana (REAL 70%)"):

        df_semana = pegar_dados()

        if df_semana is not None:
            df_semana = indicadores(df_semana)
            df_semana = filtrar_semana(df_semana)

            w, l, wr = backtest_real(df_semana)

            st.success(f"""
            📊 RESULTADO SEMANA (ESTRATÉGIA REAL)  
            Wins: {w}  
            Losses: {l}  
            Winrate: {wr:.2f}%
            """)

with col2:
    if st.button("📊 Backtest Dia Anterior (REAL 70%)"):

        df_dia = pegar_dados()

        if df_dia is not None:
            df_dia = indicadores(df_dia)

            # aproxima último período útil
            df_dia = df_dia.tail(120)

            w, l, wr = backtest_real(df_dia)

            st.info(f"""
            📊 RESULTADO DIA ANTERIOR (ESTRATÉGIA REAL)  
            Wins: {w}  
            Losses: {l}  
            Winrate: {wr:.2f}%
            """)
