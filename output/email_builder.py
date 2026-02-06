import os
import requests


def send_email(html: str):
    api_key = os.getenv("SENDGRID_API_KEY", "")
    from_email = os.getenv("SENDGRID_FROM", "")
    to_email = os.getenv("SENDGRID_TO", "")

    if not api_key or not from_email or not to_email:
        raise RuntimeError("Missing SENDGRID_API_KEY / SENDGRID_FROM / SENDGRID_TO in environment")

    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": from_email},
        "subject": "Daily Automotive Intelligence Digest",
        "content": [{"type": "text/html", "value": html}],
    }

    r = requests.post(
        "https://api.sendgrid.com/v3/mail/send",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30,
    )


    # SendGrid returns 202 Accepted on success
    if r.status_code != 202:
        raise RuntimeError(f"SendGrid failed: {r.status_code} {r.text}")
