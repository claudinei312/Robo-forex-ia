import streamlit as st
import smtplib
from email.mime.text import MIMEText

EMAIL = st.secrets["claudineialvesjunior@gmail.com"]
SENHA = st.secrets["gbin ugpq tosj owxf"]


def enviar_email(msg):
    try:
        email = MIMEText(msg)
        email["Subject"] = "🤖 Robô Forex IA"
        email["From"] = EMAIL
        email["To"] = EMAIL

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL, SENHA)
        server.send_message(email)
        server.quit()

    except Exception as e:
        print("Erro email:", e)
