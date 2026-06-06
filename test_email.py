import os
import sendgrid
from dotenv import load_dotenv
from sendgrid.helpers.mail import Mail

load_dotenv()
api_key = os.getenv("SENDGRID_API_KEY")

sg = sendgrid.SendGridAPIClient(api_key=api_key)
message = Mail(from_email="ervarishitha@gmail.com", to_emails="ervarishitha@gmail.com", subject="Test", html_content="Test")
try:
    response = sg.send(message)
    print("Success:", response.status_code)
except Exception as e:
    if hasattr(e, 'body'):
        print(e.body)
    else:
        print(e)
