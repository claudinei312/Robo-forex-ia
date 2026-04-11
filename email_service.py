import smtplib
from email.mime.text import MIMEText

EMAIL = "SEU_EMAIL"
SENHA = "SENHA_APP"

def enviar_email(msg):
    mensagem = MIMEText(msg)
    mensagem["Subject"] = "Robô Forex"
    mensagem["From"] = EMAIL
    mensagem["To"] = EMAIL

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(EMAIL, SENHA)
    server.send_message(mensagem)
    server.quit()
