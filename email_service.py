import smtplib
from email.mime.text import MIMEText

EMAIL = "claudineialvesjunior@gmail.com"
SENHA = "gbin ugpq tosj owxf"

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
