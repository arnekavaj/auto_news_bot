from email.mime.text import MIMEText
import smtplib
from config import *




def send_email(html):
    msg = MIMEText(html, "html")
    msg["Subject"] = "Daily Automotive Intelligence Digest"
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_TO


    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)